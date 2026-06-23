import preferArrowFunctions from 'eslint-plugin-prefer-arrow-functions';

import { castToEslintRule, type EslintRule } from '#create-rule';

import { noAnonymousParamType } from './no-anonymous-param-type';
import { noIdentityCast } from './no-identity-cast';
import { noReturnArrayPush } from './no-return-array-push';
import { noTypeAnnotations } from './no-type-annotations';
import { noTypePredicate } from './no-type-predicate';
import { noZodCustom } from './no-zod-custom';
import { preferDestructuredParams } from './prefer-destructured-params';

const upstreamPreferArrowFunctions = preferArrowFunctions.rules?.['prefer-arrow-functions'];
if (!upstreamPreferArrowFunctions) {
  throw new Error('eslint-plugin-prefer-arrow-functions: "prefer-arrow-functions" rule missing');
}

export const rules: Record<string, EslintRule> = {
  'no-anonymous-param-type': noAnonymousParamType,
  'no-identity-cast': noIdentityCast,
  'no-return-array-push': noReturnArrayPush,
  'no-type-annotations': noTypeAnnotations,
  'no-type-predicate': noTypePredicate,
  'no-zod-custom': noZodCustom,
  'prefer-arrow-functions': castToEslintRule(upstreamPreferArrowFunctions),
  'prefer-destructured-params': preferDestructuredParams,
};
