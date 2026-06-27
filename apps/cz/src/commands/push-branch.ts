import type { InferValue } from '@optique/core/parser';

import { object } from '@optique/core/constructs';
import { message } from '@optique/core/message';
import { command, constant, option } from '@optique/core/primitives';
import { ensure, poll } from '@zyplux/util';
import { $, readTrimmed } from '@zyplux/util/shell';

export const pushBranchCommand = command(
  'push-branch',
  object({
    command: constant('push-branch' as const),
    ready: option('-r', '--ready', {
      description: message`Flip the PR to draft, push, then mark it ready (re-triggering Copilot review) and enable auto-merge.`,
    }),
  }),
  {
    aliases: ['p'],
    brief: message`Push the current branch and open or advance its draft PR.`,
  },
);

type PushBranchConfig = InferValue<typeof pushBranchCommand>;

const readPrField = async (json: string, jq: string) => readTrimmed($.gh.pr.view({ jq, json }));

export const runPushBranch = async ({ ready }: PushBranchConfig) => {
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

  if (ready && existing === 'OPEN' && (await readPrField('isDraft', '.isDraft')) === 'false') {
    await $.gh.pr.ready({ undo: true });
  }

  await $.git.push('origin', branch, { setUpstream: true });

  if (existing !== 'OPEN') {
    await $.gh.pr.create({ base: 'main', body: '', draft: true, title: branch });
  }

  const url = await readPrField('url', '.url');
  if (!ready) {
    console.log(`PR (draft): ${url}`);
    return;
  }

  await $.gh.pr.ready();

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
