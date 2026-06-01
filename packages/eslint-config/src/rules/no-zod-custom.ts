import { AST_NODE_TYPES } from '@typescript-eslint/utils';

import { createRule } from '../create-rule';

export const noZodCustom = createRule({
  create: context => ({
    CallExpression: node => {
      if (node.callee.type !== AST_NODE_TYPES.MemberExpression) return;
      if (node.callee.object.type !== AST_NODE_TYPES.Identifier) return;
      if (node.callee.object.name !== 'z') return;
      if (node.callee.property.type !== AST_NODE_TYPES.Identifier) return;
      if (node.callee.property.name !== 'custom') return;
      context.report({
        messageId: 'noZodCustom',
        node,
      });
    },
  }),
  defaultOptions: [],
  meta: {
    docs: {
      description:
        "Disallow `z.custom<T>()`; the generic argument is an unverified type assertion that bypasses zod's runtime guarantee.",
    },
    messages: {
      noZodCustom:
        '`z.custom<T>()` is an unverified type assertion (the generic is trusted, not validated). Build the value with real zod combinators (`z.object`, `z.union`, etc.) or restructure to runtime-validate the shape.',
    },
    schema: [],
    type: 'problem',
  },
  name: 'no-zod-custom',
});
