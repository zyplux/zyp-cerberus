import { RuleTester } from '@typescript-eslint/rule-tester';
import { fileURLToPath } from 'node:url';
import { afterAll, describe, it } from 'vitest';

RuleTester.afterAll = afterAll;
RuleTester.describe = (text, callback) => {
  describe(text, callback);
};
RuleTester.it = it;
RuleTester.itOnly = it.only;

const packageRoot = fileURLToPath(new URL('..', import.meta.url));

export const ruleTester = new RuleTester();

export const typeAwareRuleTester = new RuleTester({
  languageOptions: {
    parserOptions: {
      projectService: {
        allowDefaultProject: ['*.ts*'],
        defaultProject: 'tsconfig.json',
      },
      tsconfigRootDir: packageRoot,
    },
  },
});
