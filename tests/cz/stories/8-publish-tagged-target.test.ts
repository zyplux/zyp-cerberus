import { runPublishTaggedTarget } from '@zyplux/cz/commands/publish-tagged-target';
import { loadReleaseTargets, type ReleaseTarget } from '@zyplux/cz/release-targets';
import { $ } from '@zyplux/util/shell';
import { afterEach, describe, expect, it, vi } from 'vitest';

vi.mock('@zyplux/util/shell', async importOriginal => {
  const actual = await importOriginal<typeof import('@zyplux/util/shell')>();
  return { ...actual, $: Object.assign(vi.fn(), { gh: actual.$.gh, git: actual.$.git }) };
});

const mockedDollar = vi.mocked($);

const findTarget = (targets: ReleaseTarget[], label: string) => {
  const target = targets.find(candidate => candidate.label === label);
  if (target === undefined) throw new Error(`${label} target missing from manifest`);
  return target;
};

type ShellValue = Parameters<typeof $>[1];

const renderValue = (value: ShellValue): string => {
  if (Buffer.isBuffer(value)) return value.toString();
  if (typeof value === 'string') return value;
  if (Array.isArray(value)) {
    const items: ShellValue[] = value;
    return items.map(item => renderValue(item)).join(' ');
  }
  throw new Error('unexpected shell expression in renderCall');
};

const renderCall = (call: Parameters<typeof $>) => {
  const [strings, ...values] = call;
  return strings.reduce((rendered, chunk, index) => {
    const value = values[index];
    return `${rendered}${chunk}${value === undefined ? '' : renderValue(value)}`;
  }, '');
};

const notFound = () => new Response(undefined, { status: 404 });
const ok = () => new Response(undefined, { status: 200 });

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
  mockedDollar.mockClear();
});

describe('8.1 skipping an already-published target', () => {
  it("8.1.1 logs and does nothing when the tag's version is already published", async () => {
    const targets = await loadReleaseTargets();
    const util = findTarget(targets, '@zyplux/util');
    const version = await util.readVersion();
    vi.stubGlobal('fetch', () => Promise.resolve(ok()));
    const log = vi.spyOn(console, 'log').mockReturnValue(undefined);

    await runPublishTaggedTarget({ command: 'publish-tagged-target', tag: `util-v${version}` });

    expect(log).toHaveBeenCalledWith(`@zyplux/util ${version} is already published; nothing to do`);
    expect(mockedDollar).not.toHaveBeenCalled();
  });
});

describe('8.2 publishing to each registry kind', () => {
  it('8.2.1 packs and publishes an npm target', async () => {
    const targets = await loadReleaseTargets();
    const util = findTarget(targets, '@zyplux/util');
    const version = await util.readVersion();
    vi.stubGlobal('fetch', () => Promise.resolve(notFound()));
    vi.spyOn(console, 'log').mockReturnValue(undefined);

    await runPublishTaggedTarget({ command: 'publish-tagged-target', tag: `util-v${version}` });

    const [packCall] = mockedDollar.mock.calls;
    if (packCall === undefined) throw new Error('expected $ to have been called');
    expect(mockedDollar).toHaveBeenCalledTimes(1);
    expect(renderCall(packCall)).toBe(
      `cd ${util.dir} && bun pm pack && bunx npm@latest publish ./*.tgz --access public`,
    );
  });

  it('8.2.2 builds and publishes a pypi target', async () => {
    const targets = await loadReleaseTargets();
    const cerberus = findTarget(targets, 'zyplux-cerberus');
    const version = await cerberus.readVersion();
    vi.stubGlobal('fetch', () => Promise.resolve(notFound()));
    vi.spyOn(console, 'log').mockReturnValue(undefined);

    await runPublishTaggedTarget({ command: 'publish-tagged-target', tag: `cerberus-v${version}` });

    const [buildCall] = mockedDollar.mock.calls;
    if (buildCall === undefined) throw new Error('expected $ to have been called');
    expect(mockedDollar).toHaveBeenCalledTimes(1);
    expect(renderCall(buildCall)).toBe('uv build --package zyplux-cerberus && uv publish');
  });

  it('8.2.3 requires GH_TOKEN and GITHUB_ACTOR before pushing a ghcr target', async () => {
    const targets = await loadReleaseTargets();
    const ci = findTarget(targets, 'ghcr.io/zyplux/ci');
    const version = await ci.readVersion();
    vi.stubEnv('GH_TOKEN', '');
    vi.stubEnv('GITHUB_ACTOR', '');
    vi.stubGlobal('fetch', (input: string | URL) =>
      Promise.resolve(String(input).includes('/token?') ? Response.json({ token: 'gh-token' }) : notFound()),
    );
    vi.spyOn(console, 'log').mockReturnValue(undefined);

    await expect(
      runPublishTaggedTarget({ command: 'publish-tagged-target', tag: `ci-image-v${version}` }),
    ).rejects.toThrow('GH_TOKEN is required to push to GHCR');
    expect(mockedDollar).not.toHaveBeenCalled();
  });

  it('8.2.4 tags and pushes a versioned and latest ghcr image', async () => {
    const targets = await loadReleaseTargets();
    const ci = findTarget(targets, 'ghcr.io/zyplux/ci');
    const version = await ci.readVersion();
    vi.stubEnv('GH_TOKEN', 'gh-token');
    vi.stubEnv('GITHUB_ACTOR', 'zyplux-bot');
    vi.stubGlobal('fetch', (input: string | URL) =>
      Promise.resolve(String(input).includes('/token?') ? Response.json({ token: 'gh-token' }) : notFound()),
    );
    vi.spyOn(console, 'log').mockReturnValue(undefined);

    await runPublishTaggedTarget({ command: 'publish-tagged-target', tag: `ci-image-v${version}` });

    const [loginCall, buildCall, versionPushCall, latestPushCall] = mockedDollar.mock.calls.map(call =>
      renderCall(call),
    );
    expect(loginCall).toContain('podman login ghcr.io -u zyplux-bot --password-stdin < ');
    expect(buildCall).toBe(`podman build -t ghcr.io/zyplux/ci:${version} -t ghcr.io/zyplux/ci:latest ${ci.dir}`);
    expect(versionPushCall).toBe(`podman push ghcr.io/zyplux/ci:${version}`);
    expect(latestPushCall).toBe('podman push ghcr.io/zyplux/ci:latest');
  });
});
