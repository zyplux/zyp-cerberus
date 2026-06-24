import { parseJson } from '@zyplux/util';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import * as z from 'zod';

const ROOT_DIR_PLACEHOLDER = '<rootDir>';
const packageDir = fileURLToPath(new URL('..', import.meta.url));

const ParserOptionsSchema = z.looseObject({ tsconfigRootDir: z.string() });

const PrintedConfigSchema = z.looseObject({
  languageOptions: z.looseObject({ parserOptions: ParserOptionsSchema }),
});

export const printConfig = () => {
  const printed = execFileSync('eslint', ['--print-config', 'src/index.ts'], { cwd: packageDir, encoding: 'utf8' });
  const config = parseJson(printed, PrintedConfigSchema);
  config.languageOptions.parserOptions.tsconfigRootDir = ROOT_DIR_PLACEHOLDER;
  return config;
};
