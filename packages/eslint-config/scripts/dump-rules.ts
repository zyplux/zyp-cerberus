import { execFileSync } from 'node:child_process';
import { writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { format } from 'prettier';

import { normalizeRules } from '#scripts/normalize-rules';

const packageDir = fileURLToPath(new URL('..', import.meta.url));

const printed = execFileSync('eslint', ['--print-config', 'src/index.ts'], {
  cwd: packageDir,
  encoding: 'utf8',
});

const normalized = normalizeRules(JSON.parse(printed));
const formatted = await format(JSON.stringify(normalized), { parser: 'json' });

writeFileSync(new URL('../rules.json', import.meta.url), formatted);
