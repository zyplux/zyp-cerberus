import { writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { format, resolveConfig } from 'prettier';

import { printConfig } from '#scripts/print-config';

const rulesPath = new URL('../rules.json', import.meta.url);

const prettierOptions = await resolveConfig(fileURLToPath(rulesPath));
const formatted = await format(JSON.stringify(printConfig()), {
  ...prettierOptions,
  objectWrap: 'collapse',
  parser: 'json',
});

writeFileSync(rulesPath, formatted);
