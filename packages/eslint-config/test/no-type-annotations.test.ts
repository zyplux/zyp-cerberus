import { noTypeAnnotations } from '#rules/no-type-annotations';

import { typeAwareRuleTester } from './rule-tester';

typeAwareRuleTester.run('no-type-annotations', noTypeAnnotations, {
  invalid: [
    {
      code: 'const greet = (): string => "hi";',
      errors: [{ messageId: 'removeReturnType' }],
      name: 'arrow return type is inferrable',
      output: 'const greet = () => "hi";',
    },
    {
      code: 'const obj = { greet: (): string => "hi" };',
      errors: [{ messageId: 'removeReturnType' }],
      name: 'object-literal arrow property return type',
      output: 'const obj = { greet: () => "hi" };',
    },
    {
      code: 'export const f = () => { const g = (): number => 1; return g; };',
      errors: [{ messageId: 'removeReturnType' }],
      name: 'nested arrow inside an exported boundary is still internal',
      output: 'export const f = () => { const g = () => 1; return g; };',
    },
    {
      code: 'const doubled = [1, 2, 3].map((n: number) => n * 2);',
      errors: [{ messageId: 'removeParamType' }],
      name: 'callback parameter is fixed by Array#map',
      output: 'const doubled = [1, 2, 3].map((n) => n * 2);',
    },
    {
      code: 'const handler: (a: number) => void = (a: number) => { a; };',
      errors: [{ messageId: 'removeParamType' }],
      name: 'parameter restates the declared function type — variable annotation stays',
      output: 'const handler: (a: number) => void = (a) => { a; };',
    },
    {
      code: 'const run = (cb: (x: number) => number) => cb(1); run((x: number): number => x);',
      errors: [{ messageId: 'removeParamType' }, { messageId: 'removeReturnType' }],
      name: 'callback with both a redundant return type and a contextual parameter',
      output: 'const run = (cb: (x: number) => number) => cb(1); run((x) => x);',
    },
    {
      code: 'declare const label: string; const copy: string = label;',
      errors: [{ messageId: 'removeVarType' }],
      name: 'variable restates the type of an identifier initializer',
      output: 'declare const label: string; const copy = label;',
    },
    {
      code: 'declare const box: { count: number }; const n: number = box.count;',
      errors: [{ messageId: 'removeVarType' }],
      name: 'variable restates the type of a member-access initializer',
      output: 'declare const box: { count: number }; const n = box.count;',
    },
    {
      code: 'declare const a: number; declare const b: number; const sum: number = a + b;',
      errors: [{ messageId: 'removeVarType' }],
      name: 'variable restates the type of a binary-expression initializer',
      output: 'declare const a: number; declare const b: number; const sum = a + b;',
    },
    {
      code: 'declare const ready: boolean; const blocked: boolean = !ready;',
      errors: [{ messageId: 'removeVarType' }],
      name: 'variable restates the type of a unary-expression initializer',
      output: 'declare const ready: boolean; const blocked = !ready;',
    },
    {
      code: 'declare const name: string; const greeting: string = `hi ${name}`;',
      errors: [{ messageId: 'removeVarType' }],
      name: 'variable restates the type of a template-literal initializer',
      output: 'declare const name: string; const greeting = `hi ${name}`;',
    },
    {
      code: 'interface Dog { bark(): void } declare const pet: Dog; const mine: Dog = pet;',
      errors: [{ messageId: 'removeVarType' }],
      name: 'variable restates a named interface type from an identifier initializer',
      output: 'interface Dog { bark(): void } declare const pet: Dog; const mine = pet;',
    },
    {
      code: 'declare const seed: number; class Counter { value: number = seed; }',
      errors: [{ messageId: 'removeVarType' }],
      name: 'class property restates the type of its initializer',
      output: 'declare const seed: number; class Counter { value = seed; }',
    },
  ],
  valid: [
    {
      code: 'const f = (x: number) => x;',
      name: 'standalone parameter has no contextual type, so its annotation is load-bearing',
    },
    {
      code: 'type Opt = { a?: number }; const make = (o: Opt = {}) => [o]; const z = Object.assign(make, { withDefaults: (defaults: Opt) => (options: Opt = {}) => make({ ...defaults, ...options }) });',
      name: 'a curried arrow assigned through `Object.assign` has only a self-referential contextual type (its own inferred type fed back through generic inference), so its parameter annotations are load-bearing — removing them yields implicit any',
    },
    {
      code: 'declare function pipe<A>(f: (a: A) => void): void; pipe((x: number) => { void x; });',
      name: 'a generic higher-order function infers its own type parameter FROM the annotated callback parameter, so the contextual type merely echoes the annotation — removing it collapses the parameter to `unknown`',
    },
    {
      code: 'const isString = (x: unknown): x is string => typeof x === "string";',
      name: 'type predicate return is kept',
    },
    {
      code: 'export const greet = (): string => "hi";',
      name: 'exported arrow — return annotation may be load-bearing for declaration emit',
    },
    {
      code: 'export const handler: (a: number) => void = (a: number) => {};',
      name: 'exported function is a module boundary — its parameter annotation is kept',
    },
    {
      code: 'const factorial = (n: number): number => n <= 1 ? 1 : n * factorial(n - 1);',
      name: 'recursive arrow return triggers TS7023, so the annotation is kept',
    },
    {
      code: [
        'type Result<T> = { error: false; value: T } | { error: true; message: string };',
        'const ok = <T>(value: T): Result<T> => ({ error: false, value });',
        'const r = ok(42);',
        'const out = r.error ? r.message : `got ${r.value}`;',
      ].join('\n'),
      name: 'generic return is kept — inference would widen `error: false` to boolean',
    },
    {
      code: 'const widen = (cb: (x: 1 | 2) => void) => cb(1); widen((x: number) => {});',
      name: 'parameter deliberately widens past the contextual type, so it is not redundant',
    },
    {
      code: 'declare const small: 1; const widened: number = small;',
      name: 'variable annotation widens the initializer type, so it is load-bearing',
    },
    {
      code: 'const s: Set<number> = new Set();',
      name: 'a `new` initializer infers from the annotation (generic) — never touched',
    },
    {
      code: 'declare function makeSet(): Set<number>; const s: Set<number> = makeSet();',
      name: 'a call initializer can infer from context, so the annotation is left alone',
    },
    {
      code: 'const point: { x: number } = { x: 1 };',
      name: 'an object-literal initializer is contextually typed, so the annotation is left alone',
    },
    {
      code: 'const items: number[] = [];',
      name: 'an empty-array initializer needs the annotation to infer its element type',
    },
    {
      code: 'let pending: number | undefined = undefined;',
      name: 'an `undefined` initializer widens, so the annotation is load-bearing',
    },
    {
      code: 'declare const label: string; export const copy: string = label;',
      name: 'exported variable is a module boundary — annotation kept',
    },
    {
      code: 'declare const label: string; const copy: string = label;\nexport { copy };',
      name: 'variable re-exported via a specifier is a module boundary',
    },
    {
      code: 'class A { m(x: number): number { return x; } }',
      name: 'class method parameters and return types have no contextual type here',
    },
  ],
});
