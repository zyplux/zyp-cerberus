import type { TSESTree } from '@typescript-eslint/utils';

import { AST_NODE_TYPES } from '@typescript-eslint/utils';

import { createRule } from '#create-rule';

const zodParseMethods = new Set<string>(['parse', 'parseAsync', 'safeParse', 'safeParseAsync']);

const isJsonParseCall = ({ callee }: TSESTree.CallExpression) =>
  callee.type === AST_NODE_TYPES.MemberExpression &&
  !callee.computed &&
  callee.object.type === AST_NODE_TYPES.Identifier &&
  callee.object.name === 'JSON' &&
  callee.property.type === AST_NODE_TYPES.Identifier &&
  callee.property.name === 'parse';

const isAwaitedJsonMethodCall = ({ arguments: args, callee, parent }: TSESTree.CallExpression) =>
  args.length === 0 &&
  parent.type === AST_NODE_TYPES.AwaitExpression &&
  callee.type === AST_NODE_TYPES.MemberExpression &&
  !callee.computed &&
  callee.property.type === AST_NODE_TYPES.Identifier &&
  callee.property.name === 'json';

const isZodParseConsumer = (source: TSESTree.CallExpression) => {
  const consumed = source.parent.type === AST_NODE_TYPES.AwaitExpression ? source.parent : source;
  const { parent: host } = consumed;
  return (
    host.type === AST_NODE_TYPES.CallExpression &&
    host.callee.type === AST_NODE_TYPES.MemberExpression &&
    !host.callee.computed &&
    host.callee.property.type === AST_NODE_TYPES.Identifier &&
    zodParseMethods.has(host.callee.property.name) &&
    host.arguments.includes(consumed)
  );
};

export const noUnvalidatedJson = createRule({
  create: context => ({
    CallExpression: node => {
      const isJsonParse = isJsonParseCall(node);
      if (!isJsonParse && !isAwaitedJsonMethodCall(node)) return;
      if (isZodParseConsumer(node)) return;
      context.report({
        data: { api: isJsonParse ? 'JSON.parse(…)' : 'await ….json()' },
        messageId: 'validateJson',
        node,
      });
    },
  }),
  defaultOptions: [],
  meta: {
    docs: {
      description:
        'Disallow consuming a deserialization boundary — `JSON.parse(…)` or an awaited `Response`/`Bun.file` `.json()` — without a zod schema. Both yield `any`, so any downstream `as` cast or hand-rolled `typeof`/`in` guard is unverified. The parsed value must flow directly (optionally through `await`) into a schema `.parse()`/`.safeParse()` call, e.g. `Schema.parse(JSON.parse(text))` or `Schema.parse(await response.json())`; a `readJson`/`fetchJson` helper whose body does this passes for the same reason. Targets only `JSON.parse` and a zero-argument, awaited `.json()` (the `Response`/`Bun.file` shape) — a `.json()` taking arguments (a response builder such as `c.json({…})`) or a non-awaited synchronous `.json()` is left alone.',
    },
    messages: {
      validateJson:
        '`{{api}}` produces untyped `any` at a deserialization boundary. Validate it with a zod schema: pass the result directly to a schema `.parse()`/`.safeParse()` (`Schema.parse(JSON.parse(text))`, `Schema.parse(await response.json())`), or route it through a helper that does, so the boundary returns a typed, runtime-checked value instead of an `as` cast or a hand-rolled `typeof`/`in` guard.',
    },
    schema: [],
    type: 'problem',
  },
  name: 'no-unvalidated-json',
});
