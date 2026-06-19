import { existsSync } from 'node:fs';
import { rm } from 'node:fs/promises';
import path from 'node:path';

import { $ } from './shell-harness';
import { ensure } from './util';

const clone = async () => {
  const cliArgsStart = 2;
  const [repo, ref = '', ...extraArgs] = process.argv.slice(cliArgsStart);
  ensure(repo !== undefined && extraArgs.length === 0, 'usage: clone-reference.ts <owner/name|url> [ref]');

  const isUrl = repo.includes('://') || repo.startsWith('git@');
  const url = isUrl ? repo : `https://github.com/${repo}.git`;
  const dest = `reference_clones/${path.basename(repo).replace(/\.git$/, '')}`;

  if (existsSync(dest)) {
    prompt(`${dest} exists — rm -rf and re-clone? [enter to continue, ^C to abort]`);
    await rm(dest, { force: true, recursive: true });
  }

  await $.git.clone(url, dest, ref);
};

try {
  await clone();
} catch (error) {
  console.error(`error: ${error instanceof Error ? error.message : String(error)}`);
  process.exitCode = 1;
}
