import { noArrowReturnType } from '#rules/no-arrow-return-type';

import { ruleTester } from './rule-tester';

ruleTester.run('no-arrow-return-type', noArrowReturnType, {
  invalid: [
    {
      code: 'const greet = (): string => "hi";',
      errors: [{ messageId: 'removeReturnType' }],
      name: 'arrow function with annotation',
      output: 'const greet = () => "hi";',
    },
    {
      code: 'const obj = { greet: (): string => "hi" };',
      errors: [{ messageId: 'removeReturnType' }],
      name: 'object-literal arrow property',
      output: 'const obj = { greet: () => "hi" };',
    },
    {
      code: 'const f = (x: number = 0): number => x;',
      errors: [{ messageId: 'removeReturnType' }],
      name: 'default parameter value influencing inference',
      output: 'const f = (x: number = 0) => x;',
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
      name: 'nested arrow inside an exported boundary is still internal',
      output: 'export const f = () => { const g = () => 1; return g; };',
    },
  ],
  valid: [
    'const isString = (x: unknown): x is string => typeof x === "string";',
    'const greet = () => "hi";',
    'declare function exists(): number;',
    {
      code: 'async function fetchAll(): Promise<void> {}',
      name: 'function declaration ignored — only arrow functions are checked',
    },
    {
      code: 'const greet = function(): string { return "hi"; };',
      name: 'function expression ignored — only arrow functions are checked',
    },
    {
      code: 'function compute(): number { const x = 1; return x; }',
      name: 'named function declaration ignored — only arrow functions are checked',
    },
    {
      code: 'function* gen(): Generator<number> { yield 1; }',
      name: 'generator declaration ignored — only arrow functions are checked',
    },
    {
      code: 'class A { m(): void {} }',
      name: 'class method ignored — only arrow functions are checked',
    },
    {
      code: 'class A { get x(): number { return 1; } }',
      name: 'class getter ignored — only arrow functions are checked',
    },
    {
      code: 'const obj = { greet(): string { return "hi"; } };',
      name: 'object-literal method shorthand ignored — only arrow functions are checked',
    },
    {
      code: 'export const greet = (): string => "hi";',
      name: 'exported arrow — annotation may be load-bearing for declaration emit',
    },
    {
      code: 'export default (): string => "hi";',
      name: 'default-exported arrow is a module boundary',
    },
    {
      code: 'const greet = (): string => "hi";\nexport { greet };',
      name: 'arrow re-exported via an export specifier is a module boundary',
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
