import { parseJson, readJsonSync } from '@zyplux/util';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { expect, it } from 'vitest';
import * as z from 'zod';

const eslintConfigDir = fileURLToPath(new URL('../../packages/eslint-config/', import.meta.url));
const rulesUrl = new URL('../../packages/eslint-config/rules.json', import.meta.url);
const rootDirPlaceholder = '<rootDir>';
const printConfigTimeoutMs = 30_000;

const ParserOptionsSchema = z.looseObject({ tsconfigRootDir: z.string() });
const PrintedConfigSchema = z.looseObject({
  languageOptions: z.looseObject({ parserOptions: ParserOptionsSchema }),
});

const printConfig = () => {
  const printed = execFileSync('eslint', ['--print-config', 'src/index.ts'], {
    cwd: eslintConfigDir,
    encoding: 'utf8',
  });
  const config = parseJson(printed, PrintedConfigSchema);
  config.languageOptions.parserOptions.tsconfigRootDir = rootDirPlaceholder;
  return config;
};

it(
  'eslint-config rules.json matches the resolved config (run `just dump-rules`)',
  () => {
    expect(printConfig()).toStrictEqual(readJsonSync(rulesUrl, PrintedConfigSchema));
  },
  printConfigTimeoutMs,
);
