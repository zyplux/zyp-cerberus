import { RuleTester } from '@typescript-eslint/rule-tester';
import { afterAll, describe, it } from 'vitest';

import { noZodCustom } from '../src/rules/no-zod-custom';

RuleTester.afterAll = afterAll;
RuleTester.describe = describe;
RuleTester.it = it;
RuleTester.itOnly = it.only;

const ruleTester = new RuleTester();

ruleTester.run('no-zod-custom', noZodCustom, {
  invalid: [
    {
      code: 'const schema = z.custom<string>(x => typeof x === "string");',
      errors: [{ messageId: 'noZodCustom' }],
      name: 'z.custom with generic and check',
    },
    {
      code: 'const schema = z.custom(x => typeof x === "string");',
      errors: [{ messageId: 'noZodCustom' }],
      name: 'z.custom without generic',
    },
    {
      code: 'const schema = z.custom<MyType>();',
      errors: [{ messageId: 'noZodCustom' }],
      name: 'z.custom with only generic',
    },
    {
      code: 'const result = z.custom<{ id: string }>(v => Boolean(v)).parse(input);',
      errors: [{ messageId: 'noZodCustom' }],
      name: 'z.custom chained with .parse',
    },
  ],
  valid: [
    'const schema = z.object({ id: z.string() });',
    'const schema = z.string();',
    'const schema = z.discriminatedUnion("op", [a, b]);',
    {
      code: 'const schema = other.custom<string>(x => true);',
      name: 'custom called on receiver other than `z` is not flagged (out of scope)',
    },
    {
      code: 'const schema = custom<string>(x => true);',
      name: 'unqualified `custom` call (destructured import) is not flagged (out of scope)',
    },
  ],
});
