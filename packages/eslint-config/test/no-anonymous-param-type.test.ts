import { noAnonymousParamType } from '#rules/no-anonymous-param-type';

import { ruleTester } from './rule-tester';

ruleTester.run('no-anonymous-param-type', noAnonymousParamType, {
  invalid: [
    {
      code: 'const f = (x: { a: string }) => x.a;',
      errors: [{ messageId: 'nameParameterType' }],
      name: 'a top-level inline object type on a plain parameter',
    },
    {
      code: 'const f = ({ a }: { a: string }) => a;',
      errors: [{ messageId: 'nameParameterType' }],
      name: 'a top-level inline object type on a destructured parameter',
    },
    {
      code: 'function read(opts: { id: number }) { return opts.id; }',
      errors: [{ messageId: 'nameParameterType' }],
      name: 'a function declaration parameter',
    },
    {
      code: 'const o = { read(p: { x: string }) { return p.x; } };',
      errors: [{ messageId: 'nameParameterType' }],
      name: 'an object-method parameter',
    },
    {
      code: 'const f = (a: { x: string }, b: { y: number }) => a.x;',
      errors: [{ messageId: 'nameParameterType' }, { messageId: 'nameParameterType' }],
      name: 'each parameter with an inline object type is reported',
    },
    {
      code: 'const f = (x: { a: string } | undefined) => x?.a;',
      errors: [{ messageId: 'nameParameterType' }],
      name: 'an object literal as a union member',
    },
    {
      code: 'const f = (x: Base & { a: string }) => x.a;',
      errors: [{ messageId: 'nameParameterType' }],
      name: 'an object literal as an intersection member',
    },
    {
      code: 'const f = (x: { a: string } | { b: number }) => x;',
      errors: [{ messageId: 'nameParameterType' }, { messageId: 'nameParameterType' }],
      name: 'every object literal in a union is reported separately',
    },
    {
      code: 'const f = (x: { a: string } = { a: "" }) => x.a;',
      errors: [{ messageId: 'nameParameterType' }],
      name: 'a parameter with a default value',
    },
    {
      code: 'class C { constructor(public opts: { a: string }) {} }',
      errors: [{ messageId: 'nameParameterType' }],
      name: 'a constructor parameter property',
    },
  ],
  valid: [
    {
      code: 'const f = (x: Foo) => x;',
      name: 'a named type reference',
    },
    {
      code: 'const f = (x: string) => x;',
      name: 'a primitive type',
    },
    {
      code: 'const f = x => x;',
      name: 'a parameter without a type annotation',
    },
    {
      code: 'const f = (x: string): { a: string } => ({ a: x });',
      name: 'an inline object type in return position is not a parameter',
    },
    {
      code: 'const x: { a: string } = { a: "" };',
      name: 'an inline object type on a variable is not a parameter',
    },
    {
      code: 'type T = { a: string };',
      name: 'an inline object type in a type-alias body is not a parameter',
    },
    {
      code: 'const f = (rows: { id: string }[]) => rows.length;',
      name: 'an object literal as an array element describes the container, not the parameter',
    },
    {
      code: 'const f = (x: Array<{ a: string }>) => x.length;',
      name: 'an object literal in a generic type argument describes the container, not the parameter',
    },
    {
      code: 'const f = (x: Record<string, { a: number }>) => x;',
      name: 'an object literal as a Record value describes the container, not the parameter',
    },
  ],
});
