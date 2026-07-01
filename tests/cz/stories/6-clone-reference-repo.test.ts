import { runCloneReferenceRepo } from '@zyplux/cz/commands/clone-reference-repo';
import { $ } from '@zyplux/util/shell';
import { existsSync } from 'node:fs';
import { mkdir } from 'node:fs/promises';
import path from 'node:path';
import { afterEach, describe, expect, it, vi } from 'vitest';

vi.mock('@zyplux/util/shell', () => ({ $: { git: { clone: vi.fn() } } }));

const clone = vi.mocked($.git.clone);

describe('6.1 building the clone url and destination', () => {
  afterEach(() => {
    clone.mockClear();
  });

  it('6.1.1 builds a github url and destination from an owner/name shorthand', async () => {
    await runCloneReferenceRepo({ command: 'clone-reference-repo', ref: undefined, repo: 'zyplux/util' });

    expect(clone).toHaveBeenCalledWith('https://github.com/zyplux/util.git', 'reference_clones/util', {
      depth: 1,
      singleBranch: true,
    });
  });

  it('6.1.2 uses a full url as-is and derives the destination from it', async () => {
    await runCloneReferenceRepo({
      command: 'clone-reference-repo',
      ref: undefined,
      repo: 'https://github.com/zyplux/util.git',
    });

    expect(clone).toHaveBeenCalledWith('https://github.com/zyplux/util.git', 'reference_clones/util', {
      depth: 1,
      singleBranch: true,
    });
  });

  it('6.1.3 derives the destination from a git@ ssh url, stripping the .git suffix', async () => {
    await runCloneReferenceRepo({
      command: 'clone-reference-repo',
      ref: undefined,
      repo: 'git@github.com:zyplux/util.git',
    });

    expect(clone).toHaveBeenCalledWith('git@github.com:zyplux/util.git', 'reference_clones/util', {
      depth: 1,
      singleBranch: true,
    });
  });

  it('6.1.4 passes the ref as a branch flag when given, omits it otherwise', async () => {
    await runCloneReferenceRepo({ command: 'clone-reference-repo', ref: 'v2.0.0', repo: 'zyplux/util' });

    expect(clone).toHaveBeenCalledWith('https://github.com/zyplux/util.git', 'reference_clones/util', {
      branch: 'v2.0.0',
      depth: 1,
      singleBranch: true,
    });
  });
});

describe('6.2 re-cloning over an existing destination', () => {
  const dest = path.join('reference_clones', 'existing-scratch-repo');

  afterEach(() => {
    clone.mockClear();
    vi.unstubAllGlobals();
  });

  it('6.2.1 prompts for confirmation and removes the existing destination before cloning', async () => {
    await mkdir(dest, { recursive: true });
    let promptedWith: string | undefined;
    vi.stubGlobal('prompt', (message?: string) => {
      promptedWith = message;
      return '';
    });

    await runCloneReferenceRepo({ command: 'clone-reference-repo', ref: undefined, repo: 'existing-scratch-repo' });

    expect(promptedWith).toBe(`${dest} exists — rm -rf and re-clone? [enter to continue, ^C to abort]`);
    expect(existsSync(dest)).toBe(false);
    expect(clone).toHaveBeenCalledWith('https://github.com/existing-scratch-repo.git', dest, {
      depth: 1,
      singleBranch: true,
    });
  });
});
