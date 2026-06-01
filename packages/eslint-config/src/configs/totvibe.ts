import type { ConfigWithExtends } from './types';

import { plugin } from '../plugin';

export const totvibeRules: ConfigWithExtends = {
  files: ['**/*.{ts,tsx}'],
  plugins: { '@totvibe': plugin },
  rules: {
    '@totvibe/no-inferrable-return-type': 'error',
    '@totvibe/no-type-predicate': 'error',
    '@totvibe/no-zod-custom': 'error',
    '@totvibe/prefer-arrow-functions': ['error', { returnStyle: 'implicit' }],
  },
};
