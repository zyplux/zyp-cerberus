import preferArrowFunctions from 'eslint-plugin-prefer-arrow-functions';

import { castToEslintRule } from '#create-rule';

import { noArrowReturnType } from './no-arrow-return-type';
import { noIdentityCast } from './no-identity-cast';
import { noReturnArrayPush } from './no-return-array-push';
import { noTypePredicate } from './no-type-predicate';
import { noZodCustom } from './no-zod-custom';

const upstreamPreferArrowFunctions = preferArrowFunctions.rules?.['prefer-arrow-functions'];
if (!upstreamPreferArrowFunctions) {
  throw new Error('eslint-plugin-prefer-arrow-functions: "prefer-arrow-functions" rule missing');
}

export const rules = {
  'no-arrow-return-type': noArrowReturnType,
  'no-identity-cast': noIdentityCast,
  'no-return-array-push': noReturnArrayPush,
  'no-type-predicate': noTypePredicate,
  'no-zod-custom': noZodCustom,
  'prefer-arrow-functions': castToEslintRule(upstreamPreferArrowFunctions),
};
