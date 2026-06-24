import { noUnvalidatedJson } from '#rules/no-unvalidated-json';

import { ruleTester } from './rule-tester';

ruleTester.run('no-unvalidated-json', noUnvalidatedJson, {
  invalid: [
    {
      code: 'const parsed = JSON.parse(text);',
      errors: [{ data: { api: 'JSON.parse(…)' }, messageId: 'validateJson' }],
      name: 'bare JSON.parse assigned to a variable',
    },
    {
      code: 'const parsed: unknown = JSON.parse(text);',
      errors: [{ messageId: 'validateJson' }],
      name: 'JSON.parse annotated `: unknown` (the pattern no-type-annotations cannot see)',
    },
    {
      code: 'const version = JSON.parse(text).version;',
      errors: [{ messageId: 'validateJson' }],
      name: 'member access straight off JSON.parse',
    },
    {
      code: 'normalizeRules(JSON.parse(printed));',
      errors: [{ messageId: 'validateJson' }],
      name: 'JSON.parse passed to a non-zod consumer',
    },
    {
      code: 'const body = await response.json();',
      errors: [{ data: { api: 'await ….json()' }, messageId: 'validateJson' }],
      name: 'bare awaited response.json()',
    },
    {
      code: 'const body: unknown = await tokenResponse.json();',
      errors: [{ messageId: 'validateJson' }],
      name: 'awaited .json() annotated `: unknown` (the reported example)',
    },
    {
      code: 'const data = (await Bun.file(path).json()).version;',
      errors: [{ messageId: 'validateJson' }],
      name: 'member access off an awaited Bun.file().json()',
    },
  ],
  valid: [
    {
      code: 'const parsed = Schema.parse(JSON.parse(text));',
      name: 'JSON.parse flows directly into schema.parse',
    },
    {
      code: 'const parsed = Schema.safeParse(JSON.parse(text));',
      name: 'JSON.parse flows directly into schema.safeParse',
    },
    {
      code: 'const body = Schema.parse(await response.json());',
      name: 'awaited .json() flows directly into schema.parse',
    },
    {
      code: 'const body = await Schema.parseAsync(await response.json());',
      name: 'awaited .json() flows into schema.parseAsync',
    },
    {
      code: 'const result = Config.parse(JSON.parse(readFileSync(path, "utf8")));',
      name: 'file read + JSON.parse wrapped by a schema',
    },
    {
      code: 'const text = JSON.stringify(value);',
      name: 'JSON.stringify is not a parse boundary',
    },
    {
      code: 'return c.json({ ok: true });',
      name: 'a .json() with arguments is a response builder, not a read',
    },
    {
      code: 'const query = builder.json();',
      name: 'a non-awaited synchronous .json() is left alone',
    },
  ],
});
