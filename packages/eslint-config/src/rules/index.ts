import preferArrowFunctions from 'eslint-plugin-prefer-arrow-functions';

import { castToEslintRule } from '../create-rule';
import { noInferrableReturnType } from './no-inferrable-return-type';
import { noTypePredicate } from './no-type-predicate';
import { noZodCustom } from './no-zod-custom';

const upstreamPreferArrowFunctions = preferArrowFunctions.rules?.['prefer-arrow-functions'];
if (!upstreamPreferArrowFunctions) {
  throw new Error('eslint-plugin-prefer-arrow-functions: "prefer-arrow-functions" rule missing');
}

export const rules = {
  'no-inferrable-return-type': noInferrableReturnType,
  'no-type-predicate': noTypePredicate,
  'no-zod-custom': noZodCustom,
  'prefer-arrow-functions': castToEslintRule(upstreamPreferArrowFunctions),
};
