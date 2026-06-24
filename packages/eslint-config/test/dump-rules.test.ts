import { readJsonSync } from '@zyplux/util';
import { expect, it } from 'vitest';

import { printConfig, PrintedConfigSchema } from '#scripts/print-config';

const eslintPrintConfigTimeoutMs = 30_000;

it(
  'rules.json matches the current ESLint config (run `just dump-rules`)',
  () => {
    const actual = printConfig();
    const expected = readJsonSync(new URL('../rules.json', import.meta.url), PrintedConfigSchema);
    expect(actual).toStrictEqual(expected);
  },
  eslintPrintConfigTimeoutMs,
);
