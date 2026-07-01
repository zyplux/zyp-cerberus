# @zyplux/tests-fixtures

Fake `Bun.$` shell output/promise fixtures for testing code built on `@zyplux/util`'s
shell harness. Ships TypeScript source, consumed directly under Bun.

## Install

```sh
bun add -d @zyplux/tests-fixtures
```

## Use

```ts
import { fakeShellOutput, fakeShellPromise, toArgv } from '@zyplux/tests-fixtures';
import { vi } from 'vitest';

const shellFn = vi.fn<typeof Bun.$>();
shellFn.mockImplementation((strings, ...values) => {
  console.log(strings[0]?.trim(), toArgv(values));
  return fakeShellPromise(fakeShellOutput('output'));
});
Bun.$ = shellFn;
```

- `fakeShellOutput(stdout, exitCode?)` — builds a fake `Awaited<ReturnType<typeof Bun.$.git.status>>`
  result; unimplemented accessors throw.
- `fakeShellPromise(result)` — wraps a fake result in a real `Promise` decorated with `Bun.$`'s
  chainable methods (`.cwd()`, `.quiet()`, `.nothrow()`, etc).
- `toArgv(values)` — extracts the argv array from a tagged-template call's interpolated values.
