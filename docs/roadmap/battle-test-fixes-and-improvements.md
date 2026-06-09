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

#### Version bump `0.1.0` → `0.2.0`

`package.json` — carries the change above.

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
