import unicorn from 'eslint-plugin-unicorn';

import type { ConfigWithExtends } from './types';

export const unicornConfig: ConfigWithExtends = {
  extends: [unicorn.configs.recommended],
  files: ['**/*.{ts,tsx,js,mjs,cjs}'],
  rules: {
    'unicorn/catch-error-name': 'off',
    'unicorn/name-replacements': 'off',
    'unicorn/no-return-array-push': 'off',
    'unicorn/prevent-abbreviations': 'off',
  },
};

// story-tests-ts (cerberus) mandates "<stories-dir>/N_slug.test.ts" filenames — the leading
// "N_" numbering conflicts with kebab-case, so this dir's own test files are exempt.
export const unicornStoryTestFilenames: ConfigWithExtends = {
  files: ['**/stories/*.{test,spec}.{ts,tsx}'],
  rules: {
    'unicorn/filename-case': ['error', { ignore: [/^\d+_/u] }],
  },
};
