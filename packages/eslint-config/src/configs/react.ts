import react from 'eslint-plugin-react';
import reactHooks from 'eslint-plugin-react-hooks';

import type { ConfigWithExtends } from './types';

export type ReactRenderer = 'dom' | 'ink' | 'opentui' | 'r3f' | 'react-pdf';

export type RendererGlobs = Partial<Record<ReactRenderer, string[]>>;

const reactRenderers: ReactRenderer[] = ['dom', 'ink', 'opentui', 'r3f', 'react-pdf'];

const domOnlyReactRulesOff = { 'react/no-unknown-property': 'off' } as const;

const reactBase = (files: string[], version: string) => {
  const recommended = react.configs.flat['recommended'];
  if (!recommended) {
    throw new Error('eslint-plugin-react: configs.flat.recommended is missing');
  }
  const jsxRuntime = react.configs.flat['jsx-runtime'];
  if (!jsxRuntime) {
    throw new Error('eslint-plugin-react: configs.flat[jsx-runtime] is missing');
  }
  return {
    extends: [recommended, jsxRuntime, reactHooks.configs.flat['recommended-latest']],
    files,
    settings: { react: { version } },
  } satisfies ConfigWithExtends;
};

export const reactPresets = (renderers: RendererGlobs, version: string): ConfigWithExtends[] =>
  reactRenderers.flatMap(renderer => {
    const files = renderers[renderer];
    if (files === undefined || files.length === 0) return [];
    const blocks: ConfigWithExtends[] = [reactBase(files, version)];
    if (renderer !== 'dom') {
      blocks.push({ files, rules: { ...domOnlyReactRulesOff } });
    }
    return blocks;
  });
