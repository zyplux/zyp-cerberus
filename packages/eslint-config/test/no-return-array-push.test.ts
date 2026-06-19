import { noReturnArrayPush } from '#rules/no-return-array-push';

import { typeAwareRuleTester } from './rule-tester';

typeAwareRuleTester.run('no-return-array-push', noReturnArrayPush, {
  invalid: [
    {
      code: 'declare const items: number[]; const length = items.push(1);',
      errors: [{ messageId: 'noReturnArrayPush' }],
      name: 'push length assigned to a variable',
    },
    {
      code: 'declare const items: number[]; const length = items.unshift(1);',
      errors: [{ messageId: 'noReturnArrayPush' }],
      name: 'unshift length assigned to a variable',
    },
    {
      code: 'declare const items: number[]; console.log(items.push(1));',
      errors: [{ messageId: 'noReturnArrayPush' }],
      name: 'push result passed as an argument',
    },
    {
      code: 'declare const items: number[]; void items.push(1);',
      errors: [{ messageId: 'noReturnArrayPush' }],
      name: 'push result consumed by the void operator',
    },
    {
      code: 'declare const items: number[]; async function run() { await items.push(1); }',
      errors: [{ messageId: 'noReturnArrayPush' }],
      name: 'awaiting an array push (the array case, unlike a promise-returning git push)',
    },
    {
      code: 'declare const items: number[]; declare const ready: boolean; ready && items.push(1);',
      errors: [{ messageId: 'noReturnArrayPush' }],
      name: 'push result used as a logical operand',
    },
    {
      code: 'declare const items: number[]; const add = (value: number) => items.push(value);',
      errors: [{ messageId: 'noReturnArrayPush' }],
      name: 'push returned from an arrow with a concise body (no block to split, so no suggestion)',
    },
    {
      code: 'declare const items: (number | string)[]; const length = items.push("a");',
      errors: [{ messageId: 'noReturnArrayPush' }],
      name: 'union-element array still resolves to an array receiver',
    },
    {
      code: 'declare const items: number[]; const length = items.push(1) as number;',
      errors: [{ messageId: 'noReturnArrayPush' }],
      name: 'a cast wrapping the call still consumes its return value',
    },
    {
      code: 'function run() { const items: number[] = []; return items.push(1); }',
      errors: [
        {
          messageId: 'noReturnArrayPush',
          suggestions: [
            {
              messageId: 'separateReturn',
              output: 'function run() { const items: number[] = []; items.push(1); return; }',
            },
          ],
        },
      ],
      name: 'returning the push length offers a split-into-statement suggestion',
    },
  ],
  valid: [
    {
      code: 'declare const items: number[]; items.push(1);',
      name: 'push as its own statement discards the return value',
    },
    {
      code: 'declare const items: number[]; items.unshift(1);',
      name: 'unshift as its own statement',
    },
    {
      code: 'declare const items: number[] | undefined; items?.push(1);',
      name: 'optional-chained push statement',
    },
    {
      code: 'declare const items: number[]; items.push(1) as unknown;',
      name: 'a cast around a bare push is still a discarded statement',
    },
    {
      code: 'declare const git: { push(remote: string, branch: string): Promise<void> }; async function run() { await git.push("origin", "main"); }',
      name: 'awaiting a promise-returning git push — the receiver is not an array',
    },
    {
      code: 'declare const stream: { push(chunk: unknown): boolean }; const accepted = stream.push(1);',
      name: 'a stream push returns a meaningful boolean — the receiver is not an array',
    },
    {
      code: 'declare const items: number[]; const length = items.push();',
      name: 'push with no arguments is a length read, not an append',
    },
    {
      code: 'declare const items: number[]; const length = items["push"](1);',
      name: 'computed member access is out of scope',
    },
    {
      code: 'declare function push(value: number): number; const length = push(1);',
      name: 'a free-standing push function is not an array method',
    },
    {
      code: 'declare const bag: any; const length = bag.push(1);',
      name: 'an `any` receiver is not provably an array, so it is left alone',
    },
  ],
});
