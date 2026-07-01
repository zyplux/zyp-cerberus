import { runPrintTagKind } from '@zyplux/cz/commands/print-tag-kind';
import { loadReleaseTargets, type ReleaseTarget } from '@zyplux/cz/release-targets';
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';

const findTarget = (targets: ReleaseTarget[], label: string) => {
  const target = targets.find(candidate => candidate.label === label);
  if (target === undefined) throw new Error(`${label} target missing from manifest`);
  return target;
};

describe('4.1 classifying a tag by its release target', () => {
  let cerberus: ReleaseTarget;
  let cerberusVersion: string;

  beforeAll(async () => {
    cerberus = findTarget(await loadReleaseTargets(), 'zyplux-cerberus');
    cerberusVersion = await cerberus.readVersion();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('4.1.1 prints the registry kind of the target that owns the tag', async () => {
    const log = vi.spyOn(console, 'log').mockReturnValue(undefined);

    await runPrintTagKind({ command: 'print-tag-kind', tag: `cerberus-v${cerberusVersion}` });

    expect(log).toHaveBeenCalledWith('pypi');
  });

  it('4.1.2 rejects a tag no release target owns', async () => {
    await expect(runPrintTagKind({ command: 'print-tag-kind', tag: 'mystery-v1.0.0' })).rejects.toThrow();
  });
});
