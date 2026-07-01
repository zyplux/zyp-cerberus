import { runBootstrapNpmTarget } from '@zyplux/cz/commands/bootstrap-npm-target';
import { publishNpm } from '@zyplux/cz/commands/publish-tagged-target';
import { loadReleaseTargets, type ReleaseTarget } from '@zyplux/cz/release-targets';
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';

vi.mock('@zyplux/cz/commands/publish-tagged-target', () => ({ publishNpm: vi.fn() }));

const findTarget = (targets: ReleaseTarget[], label: string) => {
  const target = targets.find(candidate => candidate.label === label);
  if (target === undefined) throw new Error(`${label} target missing from manifest`);
  return target;
};

describe('5.1 validating the target before bootstrapping', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('5.1.1 rejects a label no release target owns', async () => {
    await expect(
      runBootstrapNpmTarget({ command: 'bootstrap-npm-target', label: 'does-not-exist' }),
    ).rejects.toThrow();
  });

  it('5.1.2 rejects a target that is not an npm target', async () => {
    await expect(
      runBootstrapNpmTarget({ command: 'bootstrap-npm-target', label: 'zyplux-cerberus' }),
    ).rejects.toThrow();
  });
});

describe('5.2 bootstrapping an npm target', () => {
  let util: ReleaseTarget;
  let utilVersion: string;

  beforeAll(async () => {
    util = findTarget(await loadReleaseTargets(), '@zyplux/util');
    utilVersion = await util.readVersion();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("5.2.1 skips publishing when the target's version is already on npm", async () => {
    vi.stubGlobal('fetch', async () => new Response(null, { status: 200 }));
    const log = vi.spyOn(console, 'log').mockReturnValue(undefined);

    await runBootstrapNpmTarget({ command: 'bootstrap-npm-target', label: '@zyplux/util' });

    expect(log).toHaveBeenCalledWith(
      `@zyplux/util ${utilVersion} is already on npm — enable its trusted publisher; no bootstrap needed`,
    );
    expect(publishNpm).not.toHaveBeenCalled();
  });

  it('5.2.2 publishes the target when its version is not yet on npm', async () => {
    vi.stubGlobal('fetch', async () => new Response(null, { status: 404 }));
    const log = vi.spyOn(console, 'log').mockReturnValue(undefined);

    await runBootstrapNpmTarget({ command: 'bootstrap-npm-target', label: '@zyplux/util' });

    expect(publishNpm).toHaveBeenCalledWith(util.dir);
    expect(log).toHaveBeenCalledWith(
      `Published @zyplux/util ${utilVersion}. Enable its trusted publisher on npmjs.com; later releases publish via OIDC.`,
    );
  });
});
