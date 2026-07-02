# @zyplux/tests-fixtures

Story-test fixtures for code built on Bun and `@zyplux/util`. Fakes swap in at the lowest
boundary (`Bun.$`, `fetch`, `console`, `Bun.sleep`) so tests exercise only public interfaces.
Ships TypeScript source, consumed directly under Bun.

## Install

```sh
bun add -d @zyplux/tests-fixtures
```

## Use

Pick a base per app type from `@zyplux/tests-fixtures/story`, extend it with suite fixtures,
and keep the binding named `test`:

```ts
import { cliTest } from '@zyplux/tests-fixtures/story';

export const test = cliTest;
export { describe, expect } from 'vitest';
```

```ts
import { describe, expect, test } from '#fixtures';

describe('1.1 pushing a branch', () => {
  test('1.1.1 pushes and reports the PR url', async ({ logs, shell }) => {
    shell.on('git rev-parse --abbrev-ref HEAD', 'feat-x');
    shell.on('git push', '');

    await runPushBranch({ command: 'push-branch', hold: false, ready: false });

    expect(shell.commands).toContain('git push --set-upstream origin feat-x');
    expect(logs.logLines).toContain('PR (draft): https://github.com/acme/repo/pull/1');
  });
});
```

## Bases (`/story`)

- `libraryTest` — lazy fixtures: `shell` (fake `Bun.$`, installed only when destructured),
  `tempDir` (auto-removed scratch directory).
- `cliTest` — extends `libraryTest`; auto-silences and captures `console` (`logs`), makes
  `Bun.sleep` instant; adds lazy `network` (fake `fetch`).

## Fakes (root export)

- `createShellFake()` — routes commands (`on(pattern, ...replies)`, later routes win, the last
  reply repeats; `otherwise(reply)` sets a fallback, unrouted commands throw) and records
  `calls` (`{ argv, program }`), `commands` (rendered strings), `commandsMatching(pattern)`.
- `createConsoleCapture()` — records `logLines`/`warnLines`/`errorLines`.
- `createFetchFake()` — routes urls (`on(prefixOrRegExp, reply)`, `otherwise(reply)`) and
  records `requests`; `okResponse()`/`notFoundResponse()` build replies.
- `createTempDir()` — `path`, `write(relativePath, content)`, `remove()`.
- `fakeShellOutput(stdout, exitCode?)`, `fakeShellPromise(result)`, `toArgv(values)` — raw
  `Bun.$` doubles behind `createShellFake`.
