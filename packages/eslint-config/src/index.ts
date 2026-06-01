import prettier from 'eslint-config-prettier';
import { defineConfig, globalIgnores } from 'eslint/config';

import { base } from './configs/base';
import { perfectionistConfig } from './configs/perfectionist';
import { reactConfig } from './configs/react';
import { tanstackRoutes } from './configs/tanstack';
import { totvibeRules } from './configs/totvibe';
import { typescript } from './configs/typescript';
import { unicornConfig } from './configs/unicorn';

export { plugin } from './plugin';

const defaultIgnores = [
  '**/.output',
  '**/.nitro',
  '**/.vinxi',
  '**/.tanstack',
  '**/.wrangler',
  '**/.venv',
  '**/dist',
  '**/node_modules',
  '**/routeTree.gen.ts',
  '**/worker-configuration.d.ts',
];

export type TotvibeOptions = {
  ignores?: string[];
  react?: boolean;
  reactFiles?: string[];
  tanstack?: boolean;
  tsconfigRootDir?: string;
};

export const totvibe = (options: TotvibeOptions = {}) => {
  const {
    ignores = [],
    react = false,
    reactFiles = ['**/src/**/*.{ts,tsx}'],
    tanstack = false,
    tsconfigRootDir = process.cwd(),
  } = options;

  return defineConfig(
    globalIgnores([...defaultIgnores, ...ignores]),
    base,
    typescript(tsconfigRootDir),
    ...(react ? [reactConfig(reactFiles)] : []),
    perfectionistConfig,
    unicornConfig,
    ...(tanstack ? [tanstackRoutes] : []),
    totvibeRules,
    prettier,
  );
};
