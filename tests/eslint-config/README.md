# eslint-config tests

Black-box tests that exercise the **published** `@zyplux/eslint-config` surface — `zyplux()`, `plugin`, and the committed `rules.json` snapshot — exactly as a downstream project would.

## Why the split

The home of a test follows what it exercises:

- **Here — public behaviour:** does the preset wire a rule with the right options, expose the right config shape, and keep `rules.json` in sync? Read off the public `zyplux()` array (run through a one-rule `Linter`) or the `eslint --print-config` output. No package internals.
- **In `packages/eslint-config/test` — rule implementation:** does a custom rule report and fix correctly? These use `@typescript-eslint/rule-tester`, which needs the _typed_ rule module — a package internal — so they are white-box unit tests and stay beside the source.
