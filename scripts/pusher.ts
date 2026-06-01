import { $, ensure } from './shell-harness';

const ready = process.argv.includes('--ready') || process.argv.includes('-r');

const push = async () => {
  const branch = await $.git.currentBranch();
  ensure(branch.length > 0, 'not on any branch (detached HEAD?)');
  ensure(branch !== 'main', 'refusing to run on main');

  const existing = await $.gh.pr.state();
  if (existing === 'MERGED') {
    console.log(`PR merged; switching to main and deleting local branch '${branch}'`);
    await $.git.checkout('main');
    await $.git.pull();
    await $.git.deleteBranch(branch);
    return;
  }

  await $.git.push('origin', branch);

  if (existing === '') {
    await $.gh.pr.create('main', branch);
  }
  if (ready && (await $.gh.pr.isDraft())) {
    await $.gh.pr.ready();
  }

  const url = await $.gh.pr.url();
  if (!ready) {
    console.log(`PR (draft): ${url}`);
    return;
  }

  await $.gh.pr.merge();
  console.log(`PR (ready, auto-merge enabled): ${url}`);
};

try {
  await push();
} catch (error) {
  console.error(`error: ${error instanceof Error ? error.message : String(error)}`);
  process.exitCode = 1;
}
