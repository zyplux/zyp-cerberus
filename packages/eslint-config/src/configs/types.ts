import type { defineConfig } from 'eslint/config';

export type ConfigWithExtends = Parameters<typeof defineConfig>[number];
