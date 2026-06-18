import eslintPkg from '@zyplux/eslint-config/package.json' with { type: 'json' };

import { $ } from './shell-harness';
import { ensure, poll } from './util';

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

const readCerberusVersion = async () => {
  const pyproject = await Bun.file(new URL('../apps/cerberus/pyproject.toml', import.meta.url)).text();
  const version = /^version = "([^"]+)"/m.exec(pyproject)?.[1];
  if (version === undefined) {
    throw new Error('could not read cerberus version from apps/cerberus/pyproject.toml');
  }
  return version;
};

const buildTargets = async () => {
  const cerberusVersion = await readCerberusVersion();
  return [
    {
      isPublished: () => httpOk(`https://registry.npmjs.org/@zyplux%2feslint-config/${eslintPkg.version}`),
      label: '@zyplux/eslint-config',
      tag: `eslint-config-v${eslintPkg.version}`,
      version: eslintPkg.version,
    },
    {
      isPublished: () => httpOk(`https://pypi.org/pypi/zyplux-cerberus/${cerberusVersion}/json`),
      label: 'zyplux-cerberus',
      tag: `cerberus-v${cerberusVersion}`,
      version: cerberusVersion,
    },
  ];
};

const publish = async (target: Target, remoteHead: string) => {
  console.log(`Cutting release ${target.tag} ...`);
  const knownRuns = await $.gh.run.ids({ event: 'release', workflow: 'release.yml' });
  await $.gh.release.create(target.tag, { target: 'main' });

  console.log('Watching the publish workflow ...');
  const runId = await poll(
    () => $.gh.run.find({ event: 'release', headSha: remoteHead, knownIds: knownRuns, workflow: 'release.yml' }),
    30,
    2000,
  );
  if (runId === undefined) {
    throw new Error('publish workflow did not start; check the Actions tab');
  }
  await $.gh.run.watch(runId);

  console.log(`Verifying ${target.label} ${target.version} ...`);
  const visible = await poll(async () => ((await target.isPublished()) ? true : undefined), 10, 3000);
  ensure(visible === true, `${target.label} ${target.version} is not visible on its registry yet`);
  console.log(`Published ${target.label} ${target.version}`);
};

const release = async () => {
  const branch = await $.git.currentBranch();
  ensure(branch === 'main', `releases are cut from main, not '${branch}'`);

  const status = await $.git.status();
  ensure(status.length === 0, 'working tree is dirty; commit or stash first');

  await $.git.fetch('origin', 'main');
  const head = await $.git.revParse('HEAD');
  const remoteHead = await $.git.revParse('origin/main');
  ensure(head === remoteHead, 'local main and origin/main differ; push or pull first');

  const pending: Target[] = [];
  for (const target of await buildTargets()) {
    if (await target.isPublished()) {
      console.log(`Skipping ${target.label} ${target.version} (already published)`);
    } else if (await $.gh.release.exists(target.tag)) {
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
