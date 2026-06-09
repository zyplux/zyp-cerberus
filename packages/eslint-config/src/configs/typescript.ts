import tseslint from 'typescript-eslint';

import type { ConfigWithExtends } from './types';

export const typescript = (tsconfigRootDir: string) =>
  ({
    extends: [tseslint.configs.strictTypeChecked, tseslint.configs.stylisticTypeChecked],
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      parserOptions: {
        projectService: true,
        tsconfigRootDir,
      },
    },
    rules: {
      '@typescript-eslint/consistent-type-assertions': ['error', { assertionStyle: 'never' }],
      '@typescript-eslint/consistent-type-definitions': ['error', 'type'],
      '@typescript-eslint/no-restricted-imports': [
        'error',
        {
          patterns: [
            {
              message:
                'No parent-relative (../) imports — route through a tsconfig "paths" alias (e.g. @/foo) instead.',
              regex: String.raw`^\.\.`,
            },
          ],
        },
      ],
      '@typescript-eslint/restrict-template-expressions': ['error', { allowNumber: true }],
    },
  }) satisfies ConfigWithExtends;
