import { noIdentityCast } from '#rules/no-identity-cast';

import { ruleTester } from './rule-tester';

ruleTester.run('no-identity-cast', noIdentityCast, {
  invalid: [
    {
      code: 'const asT = (x: number) => x;',
      errors: [{ messageId: 'noIdentityCast' }],
      name: 'expression-bodied identity with a typed parameter',
    },
    {
      code: 'const asT = (x: Foo): Foo => x;',
      errors: [{ messageId: 'noIdentityCast' }],
      name: 'identity that also annotates the return position',
    },
    {
      code: 'const asT = (x: number) => { return x; };',
      errors: [{ messageId: 'noIdentityCast' }],
      name: 'block-bodied identity with a single return',
    },
    {
      code: 'function asNumber(x: number) { return x; }',
      errors: [{ messageId: 'noIdentityCast' }],
      name: 'function declaration identity',
    },
    {
      code: 'const o = { id(x: number) { return x; } };',
      errors: [{ messageId: 'noIdentityCast' }],
      name: 'object-method identity',
    },
  ],
  valid: [
    {
      code: 'const identity = <T>(x: T) => x;',
      name: 'generic identity preserves the type — the sanctioned pass-through',
    },
    {
      code: 'const identity = <T extends object>(x: T) => x;',
      name: 'constrained generic identity',
    },
    {
      code: 'const echo = (x) => x;',
      name: 'untyped parameter asserts no type, so it is not a disguised cast',
    },
    {
      code: 'const double = (x: number) => x * 2;',
      name: 'body transforms the argument',
    },
    {
      code: 'const first = (x: { a: number }) => x.a;',
      name: 'returns a property, not the parameter itself',
    },
    {
      code: 'const keepFirst = (a: number, b: number) => a;',
      name: 'more than one parameter is not an identity cast',
    },
    {
      code: 'const relay = (x: number) => { log(x); return x; };',
      name: 'block body does more than return the parameter',
    },
  ],
});
