import { execFileSync } from 'node:child_process';
import { writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { format, resolveConfig } from 'prettier';

import { normalizeRules } from '#scripts/normalize-rules';

const packageDir = fileURLToPath(new URL('..', import.meta.url));
const rulesPath = new URL('../rules.json', import.meta.url);

const printed = execFileSync('eslint', ['--print-config', 'src/index.ts'], {
  cwd: packageDir,
  encoding: 'utf8',
});

const normalized = normalizeRules(JSON.parse(printed));
const prettierOptions = await resolveConfig(fileURLToPath(rulesPath));
const formatted = await format(JSON.stringify(normalized), {
  ...prettierOptions,
  objectWrap: 'collapse',
  parser: 'json',
});

writeFileSync(rulesPath, formatted);
