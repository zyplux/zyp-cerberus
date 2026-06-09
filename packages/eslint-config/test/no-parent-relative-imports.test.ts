import { Linter } from 'eslint';
import tseslint from 'typescript-eslint';
import { describe, expect, it } from 'vitest';

import { typescript } from '#configs/typescript';

const config = typescript(import.meta.dirname);
const restrictedImportsRule = config.rules['@typescript-eslint/no-restricted-imports'];

const linter = new Linter();

const parentImportErrorCount = (code: string) =>
  linter.verify(code, {
    languageOptions: { parser: tseslint.parser },
    plugins: { '@typescript-eslint': tseslint.plugin },
    rules: { '@typescript-eslint/no-restricted-imports': restrictedImportsRule },
  }).length;

describe('no parent-relative (../) imports', () => {
  it('flags a single-level parent import', () => {
    expect(parentImportErrorCount("import { x } from '../x';")).toBe(1);
  });

  it('flags a deep parent import — regex matches every depth, unlike a glob', () => {
    expect(parentImportErrorCount("import { x } from '../../../x';")).toBe(1);
  });

  it('flags `import type` — the TS-aware variant inspects type-only imports', () => {
    expect(parentImportErrorCount("import type { X } from '../x';")).toBe(1);
  });

  it('flags `export … from` re-exports', () => {
    expect(parentImportErrorCount("export { x } from '../x';")).toBe(1);
  });

  it('allows same-directory relative imports', () => {
    expect(parentImportErrorCount("import { x } from './x';")).toBe(0);
  });

  it('allows path-alias imports', () => {
    expect(parentImportErrorCount("import { x } from '@/x';")).toBe(0);
  });

  it('allows bare package imports', () => {
    expect(parentImportErrorCount("import { x } from 'node:path';")).toBe(0);
  });

  it('leaves non-import string arguments untouched', () => {
    expect(parentImportErrorCount("const p = path.resolve(dir, '../..');")).toBe(0);
  });
});
