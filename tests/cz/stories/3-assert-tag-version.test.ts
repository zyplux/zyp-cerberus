import { runAssertTagVersion } from '@zyplux/cz/commands/assert-tag-version';
import { loadReleaseTargets, type ReleaseTarget } from '@zyplux/cz/release-targets';
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';

const findTarget = (targets: ReleaseTarget[], label: string) => {
  const target = targets.find(candidate => candidate.label === label);
  if (target === undefined) throw new Error(`${label} target missing from manifest`);
  return target;
};

describe('3.1 asserting a tag against the release manifest', () => {
  let util: ReleaseTarget;
  let utilVersion: string;

  beforeAll(async () => {
    util = findTarget(await loadReleaseTargets(), '@zyplux/util');
    utilVersion = await util.readVersion();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("3.1.1 logs a confirmation when the tag matches its target's declared version", async () => {
    const log = vi.spyOn(console, 'log').mockReturnValue(undefined);

    await runAssertTagVersion({ command: 'assert-tag-version', tag: `util-v${utilVersion}` });

    expect(log).toHaveBeenCalledWith(`@zyplux/util ${utilVersion} matches util-v${utilVersion}`);
  });

  it('3.1.2 rejects a tag no release target owns', async () => {
    await expect(runAssertTagVersion({ command: 'assert-tag-version', tag: 'mystery-v1.0.0' })).rejects.toThrow();
  });
});
