import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { expect, it } from 'vitest';

import { normalizeRules } from '#scripts/normalize-rules';

const packageDir = fileURLToPath(new URL('..', import.meta.url));

it('rules.json matches the current ESLint config (run `just dump-rules`)', () => {
  const printed = execFileSync('eslint', ['--print-config', 'src/index.ts'], {
    cwd: packageDir,
    encoding: 'utf8',
  });
  const committed = readFileSync(new URL('../rules.json', import.meta.url), 'utf8');

  expect(normalizeRules(JSON.parse(printed))).toStrictEqual(JSON.parse(committed));
});
