import vitest from '@vitest/eslint-plugin';

import type { ConfigWithExtends } from './types';

export const vitestConfig = {
  extends: [vitest.configs.recommended],
  files: ['**/*.{test,spec}.{ts,tsx}'],
  rules: {
    'vitest/expect-expect': ['error', { assertFunctionNames: ['expect', 'expect*'] }],
  },
} satisfies ConfigWithExtends;
