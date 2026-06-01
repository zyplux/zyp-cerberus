import perfectionist from 'eslint-plugin-perfectionist';

import type { ConfigWithExtends } from './types';

export const perfectionistConfig: ConfigWithExtends = {
  extends: [perfectionist.configs['recommended-natural']],
  files: ['**/*.{ts,tsx,js,mjs,cjs}'],
};
