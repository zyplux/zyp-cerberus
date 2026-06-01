import { RuleTester } from '@typescript-eslint/rule-tester';
import { afterAll, describe, it } from 'vitest';

import { noTypePredicate } from '../src/rules/no-type-predicate';

RuleTester.afterAll = afterAll;
RuleTester.describe = describe;
RuleTester.it = it;
RuleTester.itOnly = it.only;

const ruleTester = new RuleTester();

ruleTester.run('no-type-predicate', noTypePredicate, {
  invalid: [
    {
      code: 'const isString = (x: unknown): x is string => typeof x === "string";',
      errors: [{ messageId: 'noTypePredicate' }],
      name: 'arrow function user-defined type guard',
    },
    {
      code: 'function isString(x: unknown): x is string { return typeof x === "string"; }',
      errors: [{ messageId: 'noTypePredicate' }],
      name: 'function declaration user-defined type guard',
    },
    {
      code: 'const isString = function (x: unknown): x is string { return typeof x === "string"; };',
      errors: [{ messageId: 'noTypePredicate' }],
      name: 'function expression user-defined type guard',
    },
    {
      code: 'class A { isString(x: unknown): x is string { return typeof x === "string"; } }',
      errors: [{ messageId: 'noTypePredicate' }],
      name: 'class method user-defined type guard',
    },
    {
      code: 'interface I { isString(x: unknown): x is string; }',
      errors: [{ messageId: 'noTypePredicate' }],
      name: 'interface method signature user-defined type guard',
    },
    {
      code: 'type Guard = (x: unknown) => x is string;',
      errors: [{ messageId: 'noTypePredicate' }],
      name: 'function type alias user-defined type guard',
    },
    {
      code: 'declare function isString(x: unknown): x is string;',
      errors: [{ messageId: 'noTypePredicate' }],
      name: 'ambient declaration user-defined type guard',
    },
    {
      code: 'const isThis = function (this: unknown): this is string { return typeof this === "string"; };',
      errors: [{ messageId: 'noTypePredicate' }],
      name: 'this-based user-defined type guard',
    },
  ],
  valid: [
    'const isString = (x: unknown) => typeof x === "string";',
    'function isString(x: unknown) { return typeof x === "string"; }',
    {
      code: 'function assert(cond: unknown): asserts cond {}',
      name: 'assertion signature without predicate is allowed',
    },
    {
      code: 'function assertString(x: unknown): asserts x is string { if (typeof x !== "string") throw new Error(); }',
      name: 'assertion signature with predicate is allowed (runtime-throwing, distinct from pure type guard)',
    },
    {
      code: 'const greet = (): string => "hi";',
      name: 'regular typed function with no predicate',
    },
  ],
});
