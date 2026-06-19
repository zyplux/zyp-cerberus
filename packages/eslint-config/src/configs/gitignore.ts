import { includeIgnoreFile } from 'eslint/config';
import { existsSync } from 'node:fs';
import path from 'node:path';

import type { ConfigWithExtends } from './types';

export const gitignore = (root: string): ConfigWithExtends => {
  const gitignorePath = path.resolve(root, '.gitignore');
  return existsSync(gitignorePath) ? includeIgnoreFile(gitignorePath, 'gitignore') : { ignores: [], name: 'gitignore' };
};
