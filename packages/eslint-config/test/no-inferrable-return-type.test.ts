import { RuleTester } from '@typescript-eslint/rule-tester';
import { afterAll, describe, it } from 'vitest';

import { noInferrableReturnType } from '#rules/no-inferrable-return-type';

RuleTester.afterAll = afterAll;
RuleTester.describe = describe;
RuleTester.it = it;
RuleTester.itOnly = it.only;

const ruleTester = new RuleTester();

ruleTester.run('no-inferrable-return-type', noInferrableReturnType, {
  invalid: [
    {
      code: 'const greet = (): string => "hi";',
      errors: [{ messageId: 'removeReturnType' }],
      name: 'arrow function with annotation',
      output: 'const greet = () => "hi";',
    },
    {
      code: 'async function fetchAll(): Promise<void> {}',
      errors: [{ messageId: 'removeReturnType' }],
      name: 'async function declaration',
      output: 'async function fetchAll() {}',
    },
    {
      code: 'class A { m(): void {} }',
      errors: [{ messageId: 'removeReturnType' }],
      name: 'class method',
      output: 'class A { m() {} }',
    },
    {
      code: 'const obj = { greet(): string { return "hi"; } };',
      errors: [{ messageId: 'removeReturnType' }],
      name: 'object-literal method shorthand',
      output: 'const obj = { greet() { return "hi"; } };',
    },
    {
      code: 'const obj = { greet: (): string => "hi" };',
      errors: [{ messageId: 'removeReturnType' }],
      name: 'object-literal arrow property',
      output: 'const obj = { greet: () => "hi" };',
    },
    {
      code: 'function* gen(): Generator<number> { yield 1; }',
      errors: [{ messageId: 'removeReturnType' }],
      name: 'generator function — rule strips annotation; tightening would require adding generator handling',
      output: 'function* gen() { yield 1; }',
    },
    {
      code: 'const greet = function(): string { return "hi"; };',
      errors: [{ messageId: 'removeReturnType' }],
      name: 'function expression assigned to a variable',
      output: 'const greet = function() { return "hi"; };',
    },
    {
      code: 'function compute(): number { const x = 1; return x; }',
      errors: [{ messageId: 'removeReturnType' }],
      name: 'named function declaration with non-trivial body',
      output: 'function compute() { const x = 1; return x; }',
    },
    {
      code: 'const f = (x: number = 0): number => x;',
      errors: [{ messageId: 'removeReturnType' }],
      name: 'default parameter value influencing inference',
      output: 'const f = (x: number = 0) => x;',
    },
    {
      code: 'class A { get x(): number { return 1; } }',
      errors: [{ messageId: 'removeReturnType' }],
      name: 'class getter accessor',
      output: 'class A { get x() { return 1; } }',
    },
    {
      code: 'const f = (): readonly [number, string] => [1, "a"] as const;',
      errors: [{ messageId: 'removeReturnType' }],
      name: 'tuple return — `as const` literal already pins the type',
      output: 'const f = () => [1, "a"] as const;',
    },
    {
      code: 'export const f = () => { const g = (): number => 1; return g; };',
      errors: [{ messageId: 'removeReturnType' }],
      name: 'nested function inside an exported boundary is still internal',
      output: 'export const f = () => { const g = () => 1; return g; };',
    },
  ],
  valid: [
    'const isString = (x: unknown): x is string => typeof x === "string";',
    'function assert(cond: unknown): asserts cond {}',
    'const greet = () => "hi";',
    'declare function exists(): number;',
    {
      code: 'export const greet = (): string => "hi";',
      name: 'exported arrow — annotation may be load-bearing for declaration emit',
    },
    {
      code: 'export async function fetchAll(): Promise<void> {}',
      name: 'exported function declaration is a module boundary',
    },
    {
      code: 'export default (): string => "hi";',
      name: 'default-exported arrow is a module boundary',
    },
    {
      code: 'export default function compute(): number { return 1; }',
      name: 'default-exported function declaration is a module boundary',
    },
    {
      code: 'const greet = (): string => "hi";\nexport { greet };',
      name: 'function re-exported via an export specifier is a module boundary',
    },
    {
      code: 'export const api = { make(): string { return "x"; } };',
      name: 'method of an exported object literal is part of the public surface',
    },
    {
      code: 'export class A { m(): void {} }',
      name: 'method of an exported class is part of the public surface',
    },
    {
      code: 'export const A = class { m(): number { return 1; } };',
      name: 'method of an exported class expression is part of the public surface',
    },
    {
      code: 'const factorial = (n: number): number => n <= 1 ? 1 : n * factorial(n - 1);',
      name: 'recursive arrow — triggers TS7023 (implicit any return type)',
    },
    {
      code: [
        'type Result<T> = { error: false; value: T } | { error: true; message: string };',
        'const ok = <T>(value: T): Result<T> => ({ error: false, value });',
        'const r = ok(42);',
        'const out = r.error ? r.message : `got ${r.value}`;',
      ].join('\n'),
      name: 'generic erosion — `error: false` widens to boolean, breaking r.error narrowing at call sites',
    },
    {
      code: 'interface I { greet(): string; }',
      name: 'interface method signature is ambient — rule must not visit it',
    },
    {
      code: 'class A { constructor(public n: number) {} }',
      name: 'constructors have no syntactic return type so the rule cannot fire',
    },
    {
      code: 'declare class C { m(): number; }',
      name: 'class method declarations in ambient classes — no body to infer from',
    },
  ],
});
