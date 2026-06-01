import type { ConfigWithExtends } from './types';

export const tanstackRoutes: ConfigWithExtends = {
  files: ['**/routes/**/*.{ts,tsx}'],
  rules: {
    'unicorn/filename-case': [
      'error',
      {
        case: 'kebabCase',
        ignore: [/^\$[a-z][\dA-Za-z]*\.tsx?$/],
      },
    ],
  },
};
