import { $ } from './shell-harness';
import { ensure, poll, readTrimmed } from './util';

const isReady = process.argv.includes('--ready') || process.argv.includes('-r');

const readPrField = async (json: string, jq: string) => readTrimmed($.gh.pr.view({ jq, json }));

const push = async () => {
  const branch = await readTrimmed($.git.revParse('HEAD', { abbrevRef: true }));
  ensure(branch.length > 0, 'not on any branch (detached HEAD?)');
  ensure(branch !== 'main', 'refusing to run on main');

  const existing = await readTrimmed(
    $.gh.pr.list({ head: branch, jq: '.[0].state // ""', json: 'state', state: 'all' }),
  );
  if (existing === 'MERGED') {
    console.log(`PR merged; switching to main and deleting local branch '${branch}'`);
    await $.git.checkout('main');
    await $.git.pull({ ffOnly: true });
    await $.git.branch(branch, { delete: true, force: true });
    return;
  }

  await $.git.push('origin', branch, { setUpstream: true });

  if (existing !== 'OPEN') {
    await $.gh.pr.create({ base: 'main', body: '', draft: true, title: branch });
  }
  if (isReady && (await readPrField('isDraft', '.isDraft')) === 'true') {
    await $.gh.pr.ready();
  }

  const url = await readPrField('url', '.url');
  if (!isReady) {
    console.log(`PR (draft): ${url}`);
    return;
  }

  const mergeState =
    (await poll(
      async () => {
        const state = await readPrField('mergeStateStatus', '.mergeStateStatus');
        return state === 'UNKNOWN' ? undefined : state;
      },
      { attempts: 10, intervalMs: 1000 },
    )) ?? 'UNKNOWN';
  ensure(mergeState !== 'UNKNOWN', 'merge state stayed UNKNOWN; check the PR on GitHub');
  ensure(mergeState !== 'DIRTY', 'merge conflict with main — rebase or resolve, then retry');

  if (mergeState === 'CLEAN') {
    await $.gh.pr.merge({ deleteBranch: true, squash: true });
    console.log(`PR merged: ${url}`);
  } else {
    await $.gh.pr.merge({ auto: true, deleteBranch: true, squash: true });
    console.log(`PR ready, auto-merge scheduled (${mergeState}): ${url}`);
  }
};

try {
  await push();
} catch (error) {
  console.error(`error: ${error instanceof Error ? error.message : String(error)}`);
  process.exitCode = 1;
}
