import { runDepsCatalog } from '@zyplux/cz/commands/deps-catalog';
import { collectDepRepos, type DepReposReport } from '@zyplux/cz/deps-catalog';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@zyplux/cz/deps-catalog', () => ({ collectDepRepos: vi.fn() }));

const mockedCollect = vi.mocked(collectDepRepos);
const JSON_INDENT = 2;

describe('7.1 writing the resolved repos to the output file', () => {
  let dir: string;

  beforeEach(async () => {
    dir = await mkdtemp(path.join(tmpdir(), 'cz-deps-catalog-'));
  });

  afterEach(async () => {
    vi.restoreAllMocks();
    await rm(dir, { force: true, recursive: true });
  });

  it('7.1.1 writes the sorted repos as indented json and reports the count', async () => {
    const report: DepReposReport = { repos: ['https://github.com/a/a', 'https://github.com/b/b'], unresolved: [] };
    mockedCollect.mockResolvedValue(report);
    const log = vi.spyOn(console, 'log').mockReturnValue(undefined);

    await runDepsCatalog({ command: 'deps-catalog', dir, out: 'catalog.json' });

    const written = await readFile(path.join(dir, 'catalog.json'), 'utf8');
    expect(written).toBe(`${JSON.stringify(report.repos, undefined, JSON_INDENT)}\n`);
    expect(log).toHaveBeenCalledWith(`Wrote 2 source repositories to ${path.join(dir, 'catalog.json')}`);
  });

  it('7.1.2 reports unresolved dependencies alongside the written count', async () => {
    const report: DepReposReport = {
      repos: [],
      unresolved: [
        { name: 'left-pad', system: 'npm' },
        { name: 'six', system: 'pypi' },
      ],
    };
    mockedCollect.mockResolvedValue(report);
    const log = vi.spyOn(console, 'log').mockReturnValue(undefined);

    await runDepsCatalog({ command: 'deps-catalog', dir, out: 'catalog.json' });

    expect(log).toHaveBeenCalledWith('Unresolved (2) — no source repo found:');
    expect(log).toHaveBeenCalledWith('  npm\tleft-pad');
    expect(log).toHaveBeenCalledWith('  pypi\tsix');
  });
});

describe('7.2 resolving the output path', () => {
  let dir: string;

  beforeEach(async () => {
    dir = await mkdtemp(path.join(tmpdir(), 'cz-deps-catalog-'));
    mockedCollect.mockResolvedValue({ repos: [], unresolved: [] });
    vi.spyOn(console, 'log').mockReturnValue(undefined);
  });

  afterEach(async () => {
    vi.restoreAllMocks();
    await rm(dir, { force: true, recursive: true });
  });

  it('7.2.1 joins a relative --out under --dir', async () => {
    await runDepsCatalog({ command: 'deps-catalog', dir, out: 'nested/catalog.json' });

    await expect(readFile(path.join(dir, 'nested/catalog.json'), 'utf8')).resolves.toBe('[]\n');
  });

  it('7.2.2 uses an absolute --out as-is', async () => {
    const absoluteOut = path.join(dir, 'elsewhere.json');

    await runDepsCatalog({ command: 'deps-catalog', dir: '/does-not-matter', out: absoluteOut });

    await expect(readFile(absoluteOut, 'utf8')).resolves.toBe('[]\n');
  });
});
