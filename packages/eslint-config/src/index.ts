import prettier from 'eslint-config-prettier';
import { defineConfig, globalIgnores } from 'eslint/config';

import { base } from './configs/base';
import { perfectionistConfig } from './configs/perfectionist';
import { reactPresets, type RendererGlobs } from './configs/react';
import { tanstackRoutes } from './configs/tanstack';
import { totvibeRules } from './configs/totvibe';
import { typescript } from './configs/typescript';
import { unicornConfig } from './configs/unicorn';

export type { ReactRenderer, RendererGlobs } from './configs/react';
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

const defaultDomFiles = ['**/src/**/*.{ts,tsx}'];

export type ReactOption = boolean | RendererGlobs;

export type TotvibeOptions = {
  ignores?: string[];
  nonDomReactFiles?: string[];
  react?: ReactOption;
  reactFiles?: string[];
  reactVersion?: string;
  tanstack?: boolean;
  tsconfigRootDir?: string;
};

const resolveRenderers = (react: ReactOption, domFiles: string[], nonDomFiles: string[]) => {
  if (react === false) return {};
  if (react === true) {
    return { dom: domFiles, ...(nonDomFiles.length > 0 && { opentui: nonDomFiles }) };
  }
  return react;
};

const create = (options: TotvibeOptions = {}) => {
  const {
    ignores = [],
    nonDomReactFiles = [],
    react = false,
    reactFiles = defaultDomFiles,
    reactVersion = 'detect',
    tanstack = false,
    tsconfigRootDir = process.cwd(),
  } = options;

  const renderers = resolveRenderers(react, reactFiles, nonDomReactFiles);

  return defineConfig(
    globalIgnores([...defaultIgnores, ...ignores]),
    base,
    typescript(tsconfigRootDir),
    ...reactPresets(renderers, reactVersion),
    perfectionistConfig,
    unicornConfig,
    ...(tanstack ? [tanstackRoutes] : []),
    totvibeRules,
    prettier,
  );
};

export const totvibe = Object.assign(create, {
  withDefaults:
    (defaults: TotvibeOptions) =>
    (options: TotvibeOptions = {}) =>
      create({ ...defaults, ...options }),
});
