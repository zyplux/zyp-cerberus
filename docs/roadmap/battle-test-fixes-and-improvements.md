# Battle-test: fixes and improvements

Findings from adopting `@totvibe/eslint-config` in a real consumer — the
`totvibe-agent` monorepo (Bun workspaces + catalog, TypeScript project
references with `composite`/declaration emit, React 19 on two renderers: DOM for
the web app and OpenTUI for the terminal app, the Vercel AI SDK v6, and zod v4).
Adopting the preset surfaced a handful of rough edges. Some were fixed in the
preset directly; others are still carried as local overrides in the consumer and
should be upstreamed as options.

The preset did its job: nothing here is a request to weaken a rule. Most "fixes"
are about giving the preset an axis of configuration it currently lacks, so a
consumer doesn't have to reach past the preset and redefine a rule by hand.

## 1. Changes the consumer required

### 1a. Applied to the preset

#### `react.version`: `'detect'` → `'19.0'`

`src/configs/react.ts`

`version: 'detect'` asks `eslint-plugin-react` to resolve the installed `react`
package starting from the lint working directory. In a Bun workspace where
`react` is a per-app dependency (and, for the terminal app, paired with a
different JSX runtime), there is no `react` at the monorepo root where ESLint
runs, so detection fails. The plugin then warns on every run and falls back to
assuming a version — which makes version-sensitive rules nondeterministic.
Pinning to `'19.0'` removes the warning and makes behavior reproducible.

This is applied, but it hardcodes a single React version into a shared preset.
See 2a for turning it into an option.

#### Version bump `0.1.0` → `0.1.1`

`package.json` — carries the change above.

#### Generators are not expressible as arrows — `no-restricted-syntax` exempts them

`src/configs/base.ts`

There is no arrow equivalent of `function*` — generators (and async
generators, e.g. a streaming agent event loop) cannot be rewritten as arrows, so
the arrow-only rule was flagging code that _cannot_ comply. Both selectors now
carry a `[generator=false]` carve-out:

```ts
'no-restricted-syntax': [
  'error',
  { message: arrowOnlyMessage, selector: 'FunctionDeclaration[generator=false]' },
  {
    message: arrowOnlyMessage,
    selector: ':not(MethodDefinition, Property[method=true]) > FunctionExpression[generator=false]',
  },
],
```

This is strictly safe — every non-generator function declaration/expression is
still banned; only the one construct arrows can't express stops being flagged.
The companion `@totvibe/prefer-arrow-functions` rule already skips generators (it
has to — it can't produce an arrow for them), so the two rules now agree on the
construct.

### 1b. Still carried as local overrides (should be upstreamed)

These are the blocks the consumer's `eslint.config.ts` had to append _after_
`...totvibe(...)` to redefine preset rules. Each is a candidate for a first-class
option so the consumer can stop hand-patching.

#### Non-DOM React renderers trip `react/no-unknown-property`

`src/configs/react.ts`

`reactConfig` applies `eslint-plugin-react`'s DOM-oriented `recommended` to every
React file. OpenTUI (a terminal renderer) uses custom host elements and props
that are not DOM attributes, so `react/no-unknown-property` rejects valid code.
The consumer turned the rule off for the terminal app:

```ts
{ files: ['apps/tui/src/**/*.{ts,tsx}'], rules: { 'react/no-unknown-property': 'off' } }
```

This is a general problem, not an OpenTUI quirk: Ink, react-three-fiber,
react-pdf, and OpenTUI are all non-DOM React renderers with their own host
namespaces. **Proposed:** see 2b.

## 2. Suggestions for `@totvibe/eslint-config`

### 2a. Make the React version an option

`TotvibeOptions.reactVersion?: string`, defaulting to `'detect'`. Consumers in a
workspace where detection fails pin it (`reactVersion: '19.0'`); standalone apps
keep autodetection. Removes the hardcoded version a shared preset shouldn't own.

### 2b. Add a non-DOM React renderer axis

Add `nonDomReactFiles?: string[]` (or `reactRenderer: 'dom' | 'custom'` scoped to
a file set). For those files, disable the DOM-specific rules
(`react/no-unknown-property`, and audit `react/void-dom-elements-no-children`,
`react/no-danger`, etc.). This makes OpenTUI/Ink/r3f first-class instead of
something each consumer discovers and patches by hand.

### 2c. Document the project-references / `no-inferrable-return-type` sharp edge

With `composite` + declaration emit, `tsc -b` can demand a return-type annotation
for portability (TS2742 "cannot be named", TS2883 non-portable inferred type) on
exactly the functions `no-inferrable-return-type` forbids annotating. The two
tools pull in opposite directions and the consumer is stuck until they discover
the escape hatches:

- annotate the _value_ with `satisfies T` inside the body instead of annotating
  the return position (the rule only inspects the return-type slot);
- route the value through a typed identity parameter
  (`const asT = (x: T) => x; return asT(value);`), since parameters carry
  portable types where a `const` binding gets control-flow-narrowed back;
- export the offending type so the inferred type _can_ be named.

These are legitimate and worth a short "interactions with TypeScript project
references" section in the preset README, so the patterns are discoverable rather
than rediscovered.

### 2d. Document the zod-at-the-boundary workflow

`consistent-type-assertions: 'never'` plus `@totvibe/no-zod-custom` and
`@totvibe/no-type-predicate` together steer every deserialization boundary
(`JSON.parse`, `WebSocket` `event.data`, JSONL records) toward a real zod schema
that _returns_ the typed value instead of `parse(x) as T`. That is the right
outcome — runtime validation, not a trusted cast — but it has a cost worth
calling out, plus one real gap:

- you hand-mirror each wire type as a schema and keep them in sync;
- the `schema: z.ZodType<T>` annotation pattern (which lets a hand-written
  schema keep its declared type) only catches schemas that produce values
  _outside_ `T`. It does **not** catch a schema that is _missing_ a union member
  — a narrower output is still assignable to the wider `T`. So a discriminated
  union can silently drop a case and stay green.

A documented recipe (the `z.ZodType<T>` discriminated-union pattern) plus a note
about the missing-member blind spot would save consumers the trial-and-error.

### 2e. The two arrow-function rules overlap (intentionally)

`no-restricted-syntax` (in `base`) and `@totvibe/prefer-arrow-functions` (in
`totvibe`) both steer toward arrow functions and both fire on the easy case (a
plain `function foo() {}` with no `this`/`arguments`), so a single violation can
surface as either message. But they are complementary, not duplicates:
`prefer-arrow-functions` auto-fixes the safe subset and backs off whenever a
function uses `this`/`arguments`/`super`/`new.target` (it can't emit a correct
arrow); `no-restricted-syntax` is the strict backstop that flags exactly those
hard cases and forces a redesign. Removing either changes what's enforced —
dropping `no-restricted-syntax` would silently legalize `this`/`arguments`
functions; dropping `prefer-arrow-functions` would lose the autofix and
object-shorthand-method coverage.

They no longer disagree about generators: both now skip them (§1a, generator
carve-out). The only redundancy left is the double report on the easy case,
which isn't worth losing the strict backstop's `this`/`arguments` coverage to
remove.

## 3. Error-message improvements

Good messages already exist (`no-zod-custom` and `no-type-predicate` both name
the construct _and_ the sanctioned alternative — keep that as the bar). The gaps
are the messages that say _what_ is wrong without saying _how_ to comply.

### `no-inferrable-return-type` → name the escape hatches

Current:

> Explicit return type annotation is unnecessary; let TypeScript infer it.

When the annotation exists to satisfy `tsc -b` portability (2c), "just remove it"
is wrong and the author has no next step. Suggested:

> Explicit return type annotation is unnecessary; let TypeScript infer it. If
> `tsc` needs it for declaration-emit portability (TS2742/TS2883), annotate the
> returned value with `satisfies` or export the referenced type instead of
> annotating the return position.

The auto-fix is also a trap here: it strips the annotation and reintroduces the
TS error. Consider downgrading the fix to a _suggestion_ (so it isn't applied by
`--fix` blindly) when a return type is present, or documenting that `--fix` can
break project-reference builds.

#### `no-restricted-syntax` (arrow-only) → acknowledge generators — applied

The message used to end "If `this`/`arguments`/`new.target`/generators are
needed, redesign", but generators have no arrow form so "redesign" was not always
possible. Now that the rule exempts generators (§1a, generator carve-out), the
`generators` clause is dropped so the message stops advising a redesign the rule
no longer requires:

> Use an arrow function. If `this`/`arguments`/`new.target` are needed, redesign.

#### `react/no-unknown-property` on a non-DOM renderer → point at the renderer

When the rule fires inside a non-DOM React renderer, the property is not unknown
— it belongs to a different host namespace. The preset can't change the upstream
message, but documenting the cause and the `nonDomReactFiles` fix (2b) next to
the rule turns a confusing "unknown property `…`" into an actionable one.

#### General principle

Every custom-rule message should answer "what do I write instead?" in one clause.
`no-zod-custom` and `no-type-predicate` already do; `no-inferrable-return-type`'s
`removeReturnType` is the one that doesn't, because its honest answer is
context-dependent (usually "remove it", sometimes "keep it and use `satisfies`").
Encode that fork in the message.
