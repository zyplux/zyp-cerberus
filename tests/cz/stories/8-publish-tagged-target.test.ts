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

const renderCall = (call: unknown[]) => {
  const [strings, ...values] = call as [TemplateStringsArray, ...unknown[]];
  return strings.reduce((rendered, chunk, index) => `${rendered}${chunk}${index < values.length ? String(values[index]) : ''}`, '');
};

const notFound = () => new Response(null, { status: 404 });
const ok = () => new Response(null, { status: 200 });

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
    vi.stubGlobal('fetch', async () => ok());
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
    vi.stubGlobal('fetch', async () => notFound());
    vi.spyOn(console, 'log').mockReturnValue(undefined);

    await runPublishTaggedTarget({ command: 'publish-tagged-target', tag: `util-v${version}` });

    expect(mockedDollar).toHaveBeenCalledTimes(1);
    expect(renderCall(mockedDollar.mock.calls[0]!)).toBe(
      `cd ${util.dir} && bun pm pack && bunx npm@latest publish ./*.tgz --access public`,
    );
  });

  it('8.2.2 builds and publishes a pypi target', async () => {
    const targets = await loadReleaseTargets();
    const cerberus = findTarget(targets, 'zyplux-cerberus');
    const version = await cerberus.readVersion();
    vi.stubGlobal('fetch', async () => notFound());
    vi.spyOn(console, 'log').mockReturnValue(undefined);

    await runPublishTaggedTarget({ command: 'publish-tagged-target', tag: `cerberus-v${version}` });

    expect(mockedDollar).toHaveBeenCalledTimes(1);
    expect(renderCall(mockedDollar.mock.calls[0]!)).toBe('uv build --package zyplux-cerberus && uv publish');
  });

  it('8.2.3 requires GH_TOKEN and GITHUB_ACTOR before pushing a ghcr target', async () => {
    const targets = await loadReleaseTargets();
    const ci = findTarget(targets, 'ghcr.io/zyplux/ci');
    const version = await ci.readVersion();
    vi.stubEnv('GH_TOKEN', '');
    vi.stubEnv('GITHUB_ACTOR', '');
    vi.stubGlobal('fetch', async (input: string | URL) =>
      String(input).includes('/token?') ? Response.json({ token: 'gh-token' }) : notFound(),
    );
    vi.spyOn(console, 'log').mockReturnValue(undefined);

    await expect(runPublishTaggedTarget({ command: 'publish-tagged-target', tag: `ci-image-v${version}` })).rejects.toThrow(
      'GH_TOKEN is required to push to GHCR',
    );
    expect(mockedDollar).not.toHaveBeenCalled();
  });

  it('8.2.4 tags and pushes a versioned and latest ghcr image', async () => {
    const targets = await loadReleaseTargets();
    const ci = findTarget(targets, 'ghcr.io/zyplux/ci');
    const version = await ci.readVersion();
    vi.stubEnv('GH_TOKEN', 'gh-token');
    vi.stubEnv('GITHUB_ACTOR', 'zyplux-bot');
    vi.stubGlobal('fetch', async (input: string | URL) =>
      String(input).includes('/token?') ? Response.json({ token: 'gh-token' }) : notFound(),
    );
    vi.spyOn(console, 'log').mockReturnValue(undefined);

    await runPublishTaggedTarget({ command: 'publish-tagged-target', tag: `ci-image-v${version}` });

    const rendered = mockedDollar.mock.calls.map(call => renderCall(call));
    expect(rendered[0]).toContain('podman login ghcr.io -u zyplux-bot --password-stdin < ');
    expect(rendered[1]).toBe(`podman build -t ghcr.io/zyplux/ci:${version} -t ghcr.io/zyplux/ci:latest ${ci.dir}`);
    expect(rendered[2]).toBe(`podman push ghcr.io/zyplux/ci:${version}`);
    expect(rendered[3]).toBe('podman push ghcr.io/zyplux/ci:latest');
  });
});
