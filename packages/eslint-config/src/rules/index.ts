import preferArrowFunctions from 'eslint-plugin-prefer-arrow-functions';

import { castToEslintRule } from '#create-rule';

import { noAnonymousParamType } from './no-anonymous-param-type';
import { noArrowReturnType } from './no-arrow-return-type';
import { noIdentityCast } from './no-identity-cast';
import { noReturnArrayPush } from './no-return-array-push';
import { noTypeAnnotations } from './no-type-annotations';
import { noTypeNarrowing } from './no-type-narrowing';
import { noTypePredicate } from './no-type-predicate';
import { noZodCustom } from './no-zod-custom';
import { preferDestructuredParams } from './prefer-destructured-params';

const upstreamPreferArrowFunctions = preferArrowFunctions.rules?.['prefer-arrow-functions'];
if (!upstreamPreferArrowFunctions) {
  throw new Error('eslint-plugin-prefer-arrow-functions: "prefer-arrow-functions" rule missing');
}

export const rules = {
  'no-anonymous-param-type': noAnonymousParamType,
  'no-arrow-return-type': noArrowReturnType,
  'no-identity-cast': noIdentityCast,
  'no-return-array-push': noReturnArrayPush,
  'no-type-annotations': noTypeAnnotations,
  'no-type-narrowing': noTypeNarrowing,
  'no-type-predicate': noTypePredicate,
  'no-zod-custom': noZodCustom,
  'prefer-arrow-functions': castToEslintRule(upstreamPreferArrowFunctions),
  'prefer-destructured-params': preferDestructuredParams,
};
