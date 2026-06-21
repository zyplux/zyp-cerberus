import eslintPkg from '@zyplux/eslint-config/package.json' with { type: 'json' };

import { $ } from './shell-harness';
import { ensure, poll, readTrimmed } from './util';

type Target = {
  isPublished: () => Promise<boolean>;
  label: string;
  tag: string;
  version: string;
};

const httpOk = async (url: string) => {
  const response = await fetch(url);
  return response.ok;
};

const ghcrImagePublished = async (repo: string, tag: string) => {
  const tokenResponse = await fetch(`https://ghcr.io/token?scope=repository:${repo}:pull`);
  if (!tokenResponse.ok) return false;
  const body: unknown = await tokenResponse.json();
  if (typeof body !== 'object' || body === null || !('token' in body)) return false;
  const { token } = body;
  if (typeof token !== 'string') return false;
  const manifest = await fetch(`https://ghcr.io/v2/${repo}/manifests/${tag}`, {
    headers: {
      Accept: 'application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.v2+json',
      Authorization: `Bearer ${token}`,
    },
    method: 'HEAD',
  });
  return manifest.ok;
};

const splitLines = (text: string) => (text ? text.split('\n') : []);

const releaseExists = async (tag: string) =>
  (await readTrimmed($.gh.release.list({ jq: `any(.[]; .tagName == "${tag}")`, json: 'tagName' }))) === 'true';

const readCerberusVersion = async () => {
  const pyproject = await Bun.file(new URL('../apps/cerberus/pyproject.toml', import.meta.url)).text();
  const version = /^version = "([^"]+)"/m.exec(pyproject)?.[1];
  if (version === undefined) {
    throw new Error('could not read cerberus version from apps/cerberus/pyproject.toml');
  }
  return version;
};

const readImageVersion = async () => {
  const containerfile = await Bun.file(new URL('../containers/ci/Containerfile', import.meta.url)).text();
  const version = /^LABEL org\.opencontainers\.image\.version="([^"]+)"/m.exec(containerfile)?.[1];
  if (version === undefined) {
    throw new Error('could not read image version from containers/ci/Containerfile');
  }
  return version;
};

const buildTargets = async () => {
  const cerberusVersion = await readCerberusVersion();
  const imageVersion = await readImageVersion();
  return [
    {
      isPublished: async () => httpOk(`https://registry.npmjs.org/@zyplux%2feslint-config/${eslintPkg.version}`),
      label: '@zyplux/eslint-config',
      tag: `eslint-config-v${eslintPkg.version}`,
      version: eslintPkg.version,
    },
    {
      isPublished: async () => httpOk(`https://pypi.org/pypi/zyplux-cerberus/${cerberusVersion}/json`),
      label: 'zyplux-cerberus',
      tag: `cerberus-v${cerberusVersion}`,
      version: cerberusVersion,
    },
    {
      isPublished: async () => ghcrImagePublished('zyplux/ci', imageVersion),
      label: 'ghcr.io/zyplux/ci',
      tag: `ci-image-v${imageVersion}`,
      version: imageVersion,
    },
  ];
};

const publish = async (target: Target, remoteHead: string) => {
  console.log(`Cutting release ${target.tag} ...`);
  const knownRuns = splitLines(
    await readTrimmed(
      $.gh.run.list({ event: 'release', jq: '.[].databaseId', json: 'databaseId', workflow: 'release.yml' }),
    ),
  );
  await $.gh.release.create(target.tag, { generateNotes: true, target: remoteHead, title: target.tag });

  console.log('Watching the publish workflow ...');
  const newRunQuery = `[.[] | select(.headSha=="${remoteHead}")] | .[].databaseId`;
  const runId = await poll(
    async () => {
      const ids = splitLines(
        await readTrimmed(
          $.gh.run.list({ event: 'release', jq: newRunQuery, json: 'databaseId,headSha', workflow: 'release.yml' }),
        ),
      );
      return ids.find(id => !knownRuns.includes(id));
    },
    { attempts: 30, intervalMs: 2000 },
  );
  if (runId === undefined) {
    throw new Error('publish workflow did not start; check the Actions tab');
  }
  await $.gh.run.watch(runId, { exitStatus: true });

  console.log(`Verifying ${target.label} ${target.version} ...`);
  const visible = await poll(async () => ((await target.isPublished()) ? true : undefined), {
    attempts: 10,
    intervalMs: 3000,
  });
  ensure(visible === true, `${target.label} ${target.version} is not visible on its registry yet`);
  console.log(`Published ${target.label} ${target.version}`);
};

const release = async () => {
  const branch = await readTrimmed($.git.revParse('HEAD', { abbrevRef: true }));
  ensure(branch === 'main', `releases are cut from main, not '${branch}'`);

  const status = await readTrimmed($.git.status({ porcelain: true }));
  ensure(status.length === 0, 'working tree is dirty; commit or stash first');

  await $.git.fetch('origin', 'main');
  const head = await readTrimmed($.git.revParse('HEAD'));
  const remoteHead = await readTrimmed($.git.revParse('origin/main'));
  ensure(head === remoteHead, 'local main and origin/main differ; push or pull first');

  const pending: Target[] = [];
  const targets = await buildTargets();
  for (const target of targets) {
    if (await target.isPublished()) {
      console.log(`Skipping ${target.label} ${target.version} (already published)`);
    } else if (await releaseExists(target.tag)) {
      console.log(`Skipping ${target.label} ${target.version} (release ${target.tag} already exists)`);
    } else {
      pending.push(target);
    }
  }
  ensure(pending.length > 0, 'nothing to release; bump a version first');

  for (const target of pending) {
    await publish(target, remoteHead);
  }
};

try {
  await release();
} catch (error) {
  console.error(`error: ${error instanceof Error ? error.message : String(error)}`);
  process.exitCode = 1;
}
