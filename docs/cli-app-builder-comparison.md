# CLI App Builder Comparison — citty · gunshi · optique · stricli

> **Scope & grounding.** Every factual claim about a library is grounded in the source actually present under
> `reference_clones/<lib>/` in this repo (the snapshots cloned via `scripts/clone-reference.ts`). Where a capability
> is genuinely absent it is marked ❌ / "not in repo". My **opinion** section additionally factors in _your_ stated
> context (Bun runtime, Zod for validation, `enquirer` for prompts, publishing a reusable `repo-tools` package to npm).
>
> **Versions analyzed:** citty `0.2.2` · gunshi `0.35.1` · optique `1.2.0` · stricli `1.2.8`.

---

## TL;DR scorecard (my assessment, 1–5)

| Library     | Dev ergonomics | Possibilities (feature ceiling) | Architecture (modern & solid) | Best when…                                                                                                                    |
| ----------- | :------------: | :-----------------------------: | :---------------------------: | ----------------------------------------------------------------------------------------------------------------------------- |
| **optique** |      3.5       |              **5**              |            **4.5**            | You want maximal type-safety, **native Zod**, env/config/prompt/completion batteries, and accept a functional learning curve. |
| **stricli** |     **4**      |                4                |            **4.5**            | You want a turnkey **app framework** with routing, dependency-injection testability, a scaffolder, and institutional backing. |
| **gunshi**  |     **4**      |                4                |               4               | You want a **plugin ecosystem** and first-class **i18n**; you don't need colors/prompts/Zod-native.                           |
| **citty**   |      3.5       |               2.5               |              3.5              | Tiny, zero-dep, declarative CLIs where the limited feature set is acceptable.                                                 |

My pick for your `repo-tools` case is at the [bottom](#my-opinion--recommendation). The short version: **Optique** (favorite) or
**Stricli** (safer "framework" choice). citty's narrow feature ceiling makes it a weak fit for a rich, published toolset;
gunshi's strengths (plugins, i18n) aren't what your toolset needs.

---

## How this maps to your three judging criteria

- **Dev ergonomics** → Table 1 + the "Learning curve / Testability / Docs" rows, summarized per-library in the scorecard.
- **Possibilities** → Table 2 (what the _finished CLI_ can do) + the extensibility rows in Table 1.
- **Architecture** → the [Architecture deep-dives](#architecture-deep-dives) + the "modern & solid" verdict for each.

---

## Table 1 — Library-consumer developer ergonomics

_What it's like to **build** a CLI with the library._ ✅ first-class · ⚠️ partial / manual · ❌ absent.

| Feature                                          | What it means / why it matters                                              | citty `0.2.2`                                                                                                                                       | gunshi `0.35.1`                                                                                                                                                               | optique `1.2.0`                                                                                                                                                | stricli `1.2.8`                                                                                                                                                                           |
| ------------------------------------------------ | --------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **API paradigm**                                 | The mental model you adopt. Shapes everything downstream.                   | Declarative **config object** — `defineCommand({...})` is an identity helper; `runMain()` runs it.                                                  | Declarative **config object** — `define({...})` + `cli()`; plus a **plugin** layer.                                                                                           | **Functional parser-combinators** — `object()/or()/option()/command()`; the parser _is_ the spec (optparse-applicative + Zod inspired).                        | **Builder functions** — `buildCommand` / `buildRouteMap` / `buildApplication` + `run`.                                                                                                    |
| **Boilerplate for a minimal command**            | How much you type for "hello world".                                        | Low — one object + `runMain`.                                                                                                                       | Low — one `define` + `cli`.                                                                                                                                                   | Low-ish — `run(option("--name", string()))`, but each subcommand wraps fields in `object({...})`.                                                              | Moderate — every flag/positional is an object with `kind`/`parse`/`brief`; `docs.brief` is **required**.                                                                                  |
| **Type inference (def → handler)**               | Do option types flow to your handler without manual typing? Core to safety. | ⚠️ Moderate. Infers types & enum literals, but a `Record<string,…>` index signature on `ParsedArgs` lets undeclared keys typecheck (erodes safety). | ✅ Strong. `ctx.values` is fully inferred from the `args` literal; shipped `.test-d.ts` type tests.                                                                           | ✅ **Best-in-class.** The parser's _structure_ yields the exact result type, including discriminated unions from `or()` + `constant()`. No annotations needed. | ✅ Strong & **bidirectional**: you annotate the handler's flags/args types and the builder forces `parameters` to match ("form follows function"). Requires explicit handler annotations. |
| **Zod integration**                              | You said you'll use Zod. Native adapter vs hand-rolled.                     | ❌ None.                                                                                                                                            | ⚠️ Manual — call Zod yourself inside a `type:'custom'` `parse()` callback.                                                                                                    | ✅ **Native** — `@optique/zod` turns a Zod schema into a value parser (`zod()`/`zodAsync()`), auto-deriving metavar/choices.                                   | ⚠️ Manual — no adapter; call Zod in a custom `parse` fn or in the handler (docs explicitly recommend Zod at the handler level).                                                           |
| **Standard Schema support**                      | Interop with the whole validator ecosystem (Zod/Valibot/ArkType).           | ❌                                                                                                                                                  | ❌ (grep finds no Standard Schema).                                                                                                                                           | ✅ via `@optique/config` (config-file validation against any Standard Schema), plus `@optique/valibot`.                                                        | ❌                                                                                                                                                                                        |
| **Built-in value parsers / validators**          | Typed coercion you get for free.                                            | ⚠️ Only `required` + `enum` membership. No numeric coercion.                                                                                        | ⚠️ `string/number/boolean/positional/enum/custom`; `required`, `multiple`, `conflicts`.                                                                                       | ✅ **Huge library**: integer/float/choice/url/uuid/port/ip/cidr/email/semver/json/fileSize/locale… each with constraints.                                      | ⚠️ `booleanParser`/`numberParser`/`buildChoiceParser`; everything else is a custom `InputParser`.                                                                                         |
| **Custom coercion / parsers**                    | Escape hatch for bespoke types.                                             | ❌ No validator/coercion hook.                                                                                                                      | ✅ `type:'custom'` `parse(value)` (throw to reject).                                                                                                                          | ✅ Implement `ValueParser` (easy) or a full `Parser` (advanced); async supported.                                                                              | ✅ `InputParser<T> = (this, input) => T \| Promise<T>` — any function.                                                                                                                    |
| **Subcommand definition**                        | Multi-command CLIs (your `release`/`push`/`clone`).                         | ✅ `subCommands` map; nested; default subcommand; aliases.                                                                                          | ✅ `subCommands` object/Map; arbitrarily nested.                                                                                                                              | ✅ `command()` + `or()`; nested; aliases (1.1.0). Dispatch is **yours to write** (or use `@optique/discover`).                                                 | ✅ `buildRouteMap({routes})`; arbitrarily nested; `defaultCommand`.                                                                                                                       |
| **Lazy / dynamic command loading**               | Fast startup for big CLIs; bundler code-splitting.                          | ✅ `Resolvable<T>` (`() => import(...)`).                                                                                                           | ✅ `lazy(() => import(...))`.                                                                                                                                                 | ✅ `@optique/discover` file-based discovery; combinators are values you can import lazily.                                                                     | ✅ Per-command `loader: () => import(...)`, awaited only after args parse.                                                                                                                |
| **Default values**                               | Optional flags with sensible defaults.                                      | ✅ `default` per arg.                                                                                                                               | ✅ `default` per arg.                                                                                                                                                         | ✅ `withDefault(parser, value \| () => value)`.                                                                                                                | ✅ `default` per parameter (incl. variadic array defaults).                                                                                                                               |
| **Env-var binding (built-in)**                   | Read config from env without glue code.                                     | ❌ (only documented in prose).                                                                                                                      | ❌                                                                                                                                                                            | ✅ `@optique/env` (`bindEnv`, documented CLI > env > .env > default precedence).                                                                               | ❌ (only Stricli's own `STRICLI_*` vars; you wire env via the context).                                                                                                                   |
| **Config-file loading (built-in)**               | File-based defaults.                                                        | ❌                                                                                                                                                  | ❌                                                                                                                                                                            | ✅ `@optique/config` (`bindConfig`, Standard-Schema-validated, documented precedence).                                                                         | ❌ (delegated to your context).                                                                                                                                                           |
| **Programmatic invocation (no real process)**    | Run a command from code/tests without touching argv/exit.                   | ✅ `runCommand(cmd,{rawArgs,data})`.                                                                                                                | ✅ `cli(argv, …)`; `usageSilent` returns rendered string.                                                                                                                     | ✅ `parse(parser,args)` is pure; `run()` accepts injected `args/stdout/stderr/onExit`.                                                                         | ✅ `run(app, inputs, context)`; `runApplication` returns the exit code; `proposeCompletions` callable.                                                                                    |
| **Testability / DI model**                       | How easily handlers are unit-tested.                                        | ⚠️ Functions are callable; `data` passthrough; no DI seam.                                                                                          | ✅ `createCommandContext` test seam; extensions are plain objects.                                                                                                            | ✅ Inject IO into `run()`; pure `parse()`; repo itself uses property-based tests.                                                                              | ✅ **Signature feature** — handler is bound to an injectable `this` context; test via `func.call(fakeCtx, flags, …)`. Reference fakes shipped.                                            |
| **Error handling for the consumer**              | Quality of the failure surface you program against.                         | ⚠️ `CLIError` with codes; `runMain` prints usage+message then `exit(1)`.                                                                            | ⚠️ Parse errors don't throw — land in `ctx.validationError` for the renderer; runtime errors flow through `onErrorCommand`.                                                   | ✅ Structured `Message` objects; configurable `aboveError`, exit codes, per-parser `errors`.                                                                   | ✅ Typed `ArgumentScannerError` subclasses; handlers may `throw` **or** `return new Error()`; `determineExitCode` maps codes; **all** arg errors aggregated.                              |
| **Extensibility (plugins / middleware / hooks)** | Cross-cutting behavior, shared infra across commands.                       | ⚠️ Plugin `setup`/`cleanup` lifecycle; no middleware chain.                                                                                         | ✅ **Rich plugin system**: dependency resolution (topo-sort), renderer & command **decorators**, **context extensions** (Hono/H3-style), `onBefore/After/ErrorCommand` hooks. | ⚠️ Extend via custom parsers / value parsers / source-contexts (env/config/prompt); no middleware chain.                                                       | ⚠️ Extend via the context (inject anything) + custom parsers; no plugin/middleware system.                                                                                                |
| **Scaffolding (`create-app`)**                   | One-command project bootstrap.                                              | ❌                                                                                                                                                  | ❌                                                                                                                                                                            | ❌                                                                                                                                                             | ✅ `@stricli/create-app` (`npx @stricli/create-app`) generates single/multi-command templates + optional autocomplete.                                                                    |
| **Documentation quality**                        | How fast you get productive.                                                | ⚠️ Good README; **no JSDoc** on the public API.                                                                                                     | ✅ VitePress site, 7 design docs, big playground, JSDoc w/ `@since`.                                                                                                          | ✅ VitePress site, tutorial + large cookbook, concepts/integrations, 19 runnable patterns, exhaustive JSDoc.                                                   | ✅ Docusaurus site + in-browser **playground** (monaco) + typedoc; JSDoc on nearly everything.                                                                                            |
| **Learning curve**                               | Onboarding cost.                                                            | Low (but you hit the feature ceiling fast).                                                                                                         | Low for basics; plugin generics + i18n key-namespacing are the steep parts.                                                                                                   | **Steepest** — the combinator paradigm and the `object({type: constant(...)})` discriminant idiom take real adjustment.                                        | Low-moderate; the "types drive parsing" inversion + flag type algebra bite in advanced cases.                                                                                             |
| **Bun support (your runtime)**                   | First-class on Bun?                                                         | ⚠️ Not targeted; built on `node:util.parseArgs` (Bun implements it) so likely works — untested in repo.                                             | ✅ Explicit `playground/bun`, `devEngines` bun ≥1.1.                                                                                                                          | ✅ `engines` bun ≥1.2; **CI test matrix runs on Bun**.                                                                                                         | ✅ `examples/bun` ships.                                                                                                                                                                  |
| **Runtime breadth**                              | Where the built CLI can run.                                                | Node-focused.                                                                                                                                       | Node 22+ / Deno / Bun (npm + JSR).                                                                                                                                            | Deno / Node 20+ / Bun (3-runtime CI; npm + JSR).                                                                                                               | Runtime-agnostic core (Node/Bun/Deno examples); only needs writable stdout/stderr in the context.                                                                                         |
| **Module format**                                | Packaging fit for an npm lib.                                               | **ESM-only.**                                                                                                                                       | ESM-first (export map exposes require keys → same ESM file).                                                                                                                  | **Dual ESM + CJS** (npm) + TS source (JSR).                                                                                                                    | **Dual ESM + CJS** (tsup).                                                                                                                                                                |
| **Runtime dependencies (core)**                  | Supply-chain surface for your published tool.                               | **Zero** (parser is `node:util.parseArgs`; `scule` is a build-time devDep).                                                                         | **~Zero** for `gunshi` core (`args-tokens` and plugins are inlined/dev).                                                                                                      | **Zero** for `@optique/core`; integrations add only their target lib.                                                                                          | **Zero** for `@stricli/core`.                                                                                                                                                             |

---

## Table 2 — Richness of the resulting CLI (end-user experience)

_What your **finished CLI** can do for the people who run it._ ✅ supported · ⚠️ partial · ❌ not in repo.

| Capability                             | What it means / why it matters                        | citty                                                                                                       | gunshi                                                                                                                                  | optique                                                                                                   | stricli                                                                                                                          |
| -------------------------------------- | ----------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| **Auto help / usage**                  | Generated `--help` text.                              | ✅ USAGE/ARGS/OPTIONS/COMMANDS.                                                                             | ✅ via `@gunshi/plugin-renderer`.                                                                                                       | ✅ generated from the parser.                                                                             | ✅ USAGE/ALIASES/COMMANDS/FLAGS/ARGS.                                                                                            |
| **Help customization**                 | Theming / overriding the help layout.                 | ⚠️ `showUsage` override only.                                                                               | ✅ **3 levels** (per-command `rendering`, CLI-level renderers, plugin decorators); `@gunshi/bone` ships _no_ renderer for full control. | ✅ `brief/description/examples/footer/sectionOrder/maxWidth/showDefault/…`.                               | ✅ `fullDescription`, `customUsage`, many config toggles.                                                                        |
| **Version flag**                       | `--version`.                                          | ✅ auto from `meta.version`.                                                                                | ✅ `--version`/`-v` (plugin-global).                                                                                                    | ✅ `--version` and/or `version` subcommand.                                                               | ✅ `--version`/`-v` + optional "outdated" warning.                                                                               |
| **Nested subcommands**                 | `tool remote add …`.                                  | ✅ unbounded.                                                                                               | ✅ unbounded.                                                                                                                           | ✅ unbounded (`command()`+`or()`).                                                                        | ✅ unbounded (route maps of route maps).                                                                                         |
| **Boolean flags**                      | `--force`.                                            | ✅                                                                                                          | ✅                                                                                                                                      | ✅ (`flag()`/value-less `option`).                                                                        | ✅                                                                                                                               |
| **String / number options**            | Typed scalar options.                                 | ⚠️ string ✅; **number ❌** (no numeric arg type).                                                          | ✅ string + number.                                                                                                                     | ✅ string + integer/float (+ constraints).                                                                | ✅ string + `numberParser`.                                                                                                      |
| **Enum / choice options**              | Constrained value set, shown in help.                 | ✅ `enum` + `options`.                                                                                      | ✅ `enum` w/ `choices`.                                                                                                                 | ✅ `choice(...)`.                                                                                         | ✅ `kind:"enum"` / `buildChoiceParser`.                                                                                          |
| **Arrays / variadic options**          | `--tag a --tag b`.                                    | ❌ (parser has a dead `multiple` field, no array type).                                                     | ✅ `multiple:true`.                                                                                                                     | ✅ `multiple()`.                                                                                          | ✅ `variadic:true` (+ custom separator).                                                                                         |
| **Counter flags (`-vvv`)**             | Repeatable verbosity.                                 | ❌                                                                                                          | ❌ (short _grouping_ exists, not counting).                                                                                             | ✅ via `multiple(option(...))` length.                                                                    | ✅ `kind:"counter"`.                                                                                                             |
| **Negatable `--no-x`**                 | Turn a default-on flag off.                           | ✅                                                                                                          | ✅ per-option `negatable`.                                                                                                              | ✅ `negatableFlag()`.                                                                                     | ✅ auto for truthy-default booleans; `withNegated`.                                                                              |
| **Aliases**                            | Short + long names.                                   | ✅ per-arg + subcommand aliases.                                                                            | ⚠️ single `short` only (no multi-alias).                                                                                                | ✅ multiple names per option.                                                                             | ✅ single-letter (h reserved).                                                                                                   |
| **Required vs optional**               | Enforced presence.                                    | ✅ `required`.                                                                                              | ✅ required/optional positionals & options.                                                                                             | ✅ bare = required; `optional()`/`withDefault()` relax.                                                   | ✅ via type / `optional`.                                                                                                        |
| **Defaults shown in help**             | `(default: …)`.                                       | ✅                                                                                                          | ✅                                                                                                                                      | ✅ (`showDefault`).                                                                                       | ✅ `[default = …]`.                                                                                                              |
| **Positional args (+ variadic)**       | `tool build <dir> [files…]`.                          | ⚠️ named, optional; **no variadic positional**.                                                             | ✅ incl. optional (since 0.34).                                                                                                         | ✅ `argument()`.                                                                                          | ✅ tuple (fixed) + array (variadic, min/max).                                                                                    |
| **Strict unknown-arg handling**        | Reject typos instead of ignoring them.                | ❌ **Lenient** — unknown flags silently accepted (`strict:false`); parse failures fall back to positionals. | ✅ unknown → `AggregateError`, rendered/thrown.                                                                                         | ✅ strict by default; `passThrough()` for wrappers.                                                       | ✅ strict; typed errors per case.                                                                                                |
| **"Did you mean…" suggestions**        | Fuzzy correction for typos.                           | ❌                                                                                                          | ❌                                                                                                                                      | ✅ Levenshtein.                                                                                           | ✅ Damerau-Levenshtein (routes, flags, enum values).                                                                             |
| **Aggregated error reporting**         | Show _all_ bad args at once.                          | ❌                                                                                                          | ✅ (AggregateError).                                                                                                                    | ✅ structured.                                                                                            | ✅ collects every error before failing.                                                                                          |
| **Shell completion**                   | Tab-completion.                                       | ❌                                                                                                          | ✅ **bash/zsh/fish/powershell** (`@gunshi/plugin-completion`, via `@bomb.sh/tab`).                                                      | ✅ **bash/zsh/fish/nushell/powershell** (5 generators).                                                   | ⚠️ logic lives **in core** (`proposeCompletions`, matches runtime exactly) but installer is **bash-only** today (zsh "planned"). |
| **Dynamic / context-aware completion** | Suggest live values (branches, files…).               | ❌                                                                                                          | ✅ per-arg completion handlers.                                                                                                         | ✅ **dependency-aware** (suggests valid values given other options).                                      | ✅ per-parameter `proposeCompletions(partial)`.                                                                                  |
| **Colors / styling**                   | ANSI output.                                          | ✅ basic, honors `NO_COLOR`.                                                                                | ❌ **plain text** (no color anywhere).                                                                                                  | ✅ auto from TTY; dims defaults/choices.                                                                  | ✅ gated on color depth; `STRICLI_NO_COLOR`/`disableAnsiColor`.                                                                  |
| **Interactive prompts (built-in)**     | Ask for missing input.                                | ❌                                                                                                          | ❌                                                                                                                                      | ✅ `@optique/inquirer` (`prompt()` fallback for missing values).                                          | ❌ (out of scope; docs recommend **enquirer**/clack).                                                                            |
| **i18n / localization**                | Localized help + errors.                              | ❌                                                                                                          | ✅ **headline feature** — `@gunshi/plugin-i18n`, pluggable `TranslationAdapter`, shipped en-US/ja-JP, per-command resources.            | ❌ (English `Message`s only).                                                                             | ✅ **thorough** — every printed string overridable; `loadText(locale)` + runtime `context.locale` + fallback warning.            |
| **Examples in help**                   | "Examples:" section.                                  | ❌                                                                                                          | ✅ `examples` field.                                                                                                                    | ✅ `examples` option.                                                                                     | ✅ via `customUsage` (each line gets a `brief`).                                                                                 |
| **Man-page generation**                | `man(7)` output from the spec.                        | ❌                                                                                                          | ❌                                                                                                                                      | ✅ `@optique/man` (`generateManPage`).                                                                    | ❌                                                                                                                               |
| **Advanced relations**                 | Mutually-exclusive groups, inter-option dependencies. | ❌                                                                                                          | ⚠️ `conflicts`.                                                                                                                         | ✅ **richest** — `or()` mutually-exclusive groups → discriminated unions, `dependency()`/`conditional()`. | ⚠️ none built-in (flags are a static-key object; discriminated flag sets out of scope).                                          |

---

## Architecture deep-dives

> Lens: **how modern and solid** each design is — core abstraction, parsing engine, type-inference mechanism,
> extension model, packaging, and maturity/governance.

### citty — declarative config over the stdlib parser

- **Core abstraction.** A command is a **plain `CommandDef` object**; `defineCommand` is a no-op identity helper that only
  carries types. Lifecycle is `setup → run/subcommand → cleanup` (cleanup always runs, errors aggregated). `Resolvable<T>`
  (`T | Promise<T> | (() => …)`) makes `meta`/`args`/`subCommands` lazy.
- **Parsing engine.** Thin custom layer over **`node:util.parseArgs`** (no `mri`/`yargs-parser`). It auto-registers
  camelCase+kebab-case aliases, hand-rolls `--no-` handling, then wraps results in a **Proxy** for case-agnostic access.
  Runs `parseArgs` in `strict:false` mode — hence the lenient unknown-flag behavior.
- **Type inference.** `defineCommand<const T extends ArgsDef>` captures the arg literal; `ParsedArgs<T>` maps each key to a
  type, dropping `| undefined` when `default`/`required` is set and narrowing enums to literal unions. A trailing
  `Record<string,…>` index signature is the weak spot — undeclared keys still typecheck.
- **Extension model.** Plugin system (`{name, setup?, cleanup?}`) with ordered setup / reverse-order cleanup.
  No middleware chain.
- **Packaging / maturity.** ESM-only, zero runtime deps, single package, single primary author (unjs/`pi0`), **pre-1.0**
  (`0.2.2`) with a history of breaking changes.
- **Verdict — modern but minimal.** The stdlib-parser + declarative-object design is clean and lean, and the lifecycle
  handling is well-tested. But the feature ceiling is low (no number/arrays/counts/completion), parsing is deliberately
  lenient, and the type model leaks. Fine for small internal CLIs; a weak foundation for a _published, reused_ toolset.

### gunshi — a micro-core with everything pushed into plugins

- **Core abstraction.** A command is a declarative `Command<G>` object (or a runner fn, or a `LazyCommand`). The runtime
  value is a frozen `CommandContext<G>` carrying `values` (typed), `explicit` (which args the user actually passed),
  `positionals`, `commandPath`, `extensions`, etc. The unifying generic `GunshiParams<{args, extensions}>` threads the arg
  shape _and_ the plugin-extensions shape through every type.
- **The monorepo split is the architecture.** A tiny core (`gunshi` bundles `plugin-global` + `plugin-renderer`;
  `@gunshi/bone` bundles _nothing_) with help, version, i18n, completion, and dry-run all implemented as **optional plugins**
  wired through a `PluginContext`.
- **Parsing engine.** Delegated to the external **`args-tokens`** package; gunshi resolves the command tree, merges plugin
  global options with command args, then `resolveArgs` produces values + an `AggregateError` (no throw — the renderer decides).
- **Extension model (the headline).** `plugin({id, dependencies, setup, extension, onExtension})` with **topological
  dependency resolution** (cycle detection), **renderer + command decorators** (chained LIFO), and **context extensions**
  (a plugin's `extension(ctx,cmd)` factory lands under `ctx.extensions[id]`) — very Hono/H3-flavored.
- **i18n architecture.** A pluggable `TranslationAdapter` (4 methods), namespaced keys (`arg:name`, `_:USAGE`, `g:i18n`),
  per-command `resource(locale)` fetchers, shipped en-US/ja-JP. Locale is explicit, not auto-detected.
- **Packaging / maturity.** ESM-first, Node 22+/Deno/Bun, npm + JSR, near-zero core deps. **Pre-1.0** (`0.35.1`) but very
  active (82 tags) and willing to break.
- **Verdict — the most _composable_ design here, at the cost of moving parts.** Excellent decoupling and a genuinely
  modern plugin model; strong inference; uniquely good i18n. The costs: deep plugin generics, a hard dependency on
  `args-tokens` for all parsing semantics, no colors/prompts, and pre-1.0 churn.

### optique — parser-combinators (the "Zod for CLIs")

- **Core abstraction.** Everything is a `Parser<M, TValue, TState>` (mode = sync/async; value = produced type; state =
  internal accumulator). Phantom `$valueType`/`$stateType` arrays carry types for inference. Parsing is the classic
  **optparse-applicative two phases**: `parse()` consumes tokens and transitions state; `complete()` folds state into the
  final typed value.
- **Composition.** Primitives (`option/argument/command/flag/constant/negatableFlag`), constructs (`object/or/merge/
tuple/seq/concat/group/conditional`), modifiers (`optional/withDefault/multiple/map`). A subcommand is `command(name,
inner)`; mutually-exclusive subcommands are `or(command…, command…)`, each tagged with `constant("x")` to make a
  **discriminated union** that TS narrows.
- **Type inference (the whole point).** Each combinator computes its result type from its children's phantom tags —
  `object()` maps fields, `or()` unions branches, `withDefault()` widens to `value | default`, `multiple()` → `readonly T[]`.
  The final config type is fully inferred from parser _structure_ with no annotations. "The parser is the type."
- **Extension model.** Write a `ValueParser` (easy) or a full `Parser` (advanced). Source-contexts (`bindEnv`, `bindConfig`,
  `prompt`) layer env/config/interactive fallback onto any parser via an annotations + two-phase facade.
- **Surface breadth.** One parser definition drives help, usage, **5-shell completion** (dependency-aware), and **man pages**.
  First-class Zod/Valibot/Standard-Schema/Temporal/Git integration packages. `@optique/run` adds process glue;
  `@optique/discover` adds file-based command dispatch.
- **Packaging / maturity.** Zero-dep core, dual ESM/CJS (npm) + TS source (JSR), Deno/Node/Bun with a real 3-runtime CI
  matrix, **property-based (fast-check) tests** that dwarf the source. **1.x stable** (`1.2.0`, ~90 releases, deliberate 1.0
  milestone). Single primary author (Hong Minhee).
- **Verdict — the most _modern and rigorous_ design here.** Pure-functional, immutable, exhaustively type-inferred, and
  cross-runtime by construction. The cost is real internal complexity (the dependency/annotation/two-phase machinery is
  ~10k lines) and a steep paradigm for newcomers — but that complexity lives _in the library_, not your code. It is
  deliberately **parsing-only**: you write the command execution yourself.

### stricli — a typed application framework with dependency injection

- **Core abstractions.** Four discriminated building blocks: **Command** (a runnable unit whose handler is
  `(this: CONTEXT, flags, ...args) => void | Error | Promise<…>`), **RouteMap** (route-name → command/nested-route-map,
  with aliases/hidden/default), **Application** (root target + resolved config + localized text), and the **CommandContext**.
- **The Context / DI model (signature feature).** The minimal context is just writable `stdout`/`stderr`. Handlers are
  invoked with `func.call(context, flags, ...args)` — so the context is `this`. You extend it with anything (db clients,
  loggers, `fs`/`os`/`path`), and `forCommand(info)` lazily builds a per-command context (a throw there becomes a distinct
  `ContextLoadError` exit code). Nothing is a hidden global ⇒ handlers are trivially unit-testable.
- **Parsing engine.** Fully custom, **two scanners**: a _route scanner_ walks route maps to find the target command (handling
  `--help`/`--helpAll`/`--` /defaults), then an _argument scanner_ (`next(input)` state machine) parses flags vs positionals,
  niladic/counter/variadic flags, batched shorthand (`-abc`), `--no-x`, and `--`. Flag + positional parsers run concurrently
  and **all** errors are aggregated.
- **Type inference.** Inverted: you annotate the handler's flag/arg types and the `TypedFlagParameter` / `TypedPositionalParameters`
  conditional-type algebra forces the `parameters` object to match (with documented `NoInfer`/constraint workarounds to dodge
  TS inference bugs). A compile-only test suite guards it.
- **End-user UX, mostly free.** Help/`--helpAll`, version (+ outdated warning), "did you mean", colors, **completion logic in
  core** (`proposeCompletions`, so completions exactly match runtime behavior), and a **full localization layer** (every
  string overridable, per-locale `loadText`).
- **Packaging / maturity.** Zero-dep core, dual ESM/CJS, runtime-agnostic (Node/Bun/Deno examples), plus a `create-app`
  scaffolder. **Bloomberg open-source**, Apache-2.0, with real governance: CODEOWNERS, DCO sign-off, OpenSSF Scorecard CI, nx
  conventional-commit releases. **1.x stable** (`1.2.8`, ~20 months, breaking changes rare).
- **Verdict — the most _solid "application framework"_ here.** Clean separation of concerns, true DI, excellent testability,
  and the strongest project hygiene/governance of the four. Costs: an intricate flag type algebra that can emit confusing
  errors in edge cases, bash-only completion installer today, and no built-in schema/env/config/prompt (all delegated to
  the context).

---

## Side-by-side on your three criteria

### Dev ergonomics

- **Smoothest to adopt:** **stricli** and **gunshi** (conventional declarative/builder feel, strong docs, scaffolder for stricli).
- **Most powerful once learned, steepest to learn:** **optique** (combinators) — but it pays you back with the best inference and **native Zod**.
- **Simplest but capped:** **citty** — quick to start, but you outgrow its feature ceiling fast.

### Possibilities

- **Highest ceiling:** **optique** — Zod/Valibot/Standard-Schema, env+config+prompt, 5-shell dependency-aware completion, man pages, mutually-exclusive groups.
- **High, with a standout:** **gunshi** (i18n + plugin ecosystem), **stricli** (counter flags, i18n, in-core completion, did-you-mean) — stricli's gaps are env/config/prompt/Zod and non-bash completion.
- **Lowest:** **citty** (no number/arrays/counts/completion/prompts/i18n).

### Architecture

- **Most modern & rigorous:** **optique** (pure-functional, property-tested, cross-runtime CI).
- **Most solid & best-governed:** **stricli** (clean DI framework, Bloomberg hygiene, 1.x stable).
- **Most composable:** **gunshi** (plugin/decorator/context-extension model) — but more moving parts and pre-1.0.
- **Cleanest-but-minimal:** **citty** — clean and lean, but the low feature ceiling limits it for production reuse.

---

## My opinion & recommendation

For **`repo-tools` — a reusable, npm-published, Bun-first CLI toolkit, validated with Zod, prompts via enquirer** — the
realistic shortlist is **optique** and **stricli**. citty and gunshi are eliminated for your case: citty has the lowest
feature ceiling (no numeric options, no arrays/counts, no completion/prompts/i18n); gunshi's headline strengths (plugin
ecosystem, i18n) aren't things a repo-automation toolset needs, and it ships no colors and no Zod-native path.

**My favorite: Optique.** It lines up with your stated stack better than anything else here:

- **Zod is native** (`@optique/zod` schema → value parser) — the only library with a real adapter, and you said Zod is a given.
- **Bun is a first-class, CI-tested target**, alongside Node and Deno.
- **"Rich and convenient" is built-in:** env binding, config files, interactive prompts, 5-shell dependency-aware completion,
  even man pages — all derived from one parser definition. That is a lot of the "future enhancement and expansion" you mentioned,
  already in the box.
- **Best-in-class type-safety**, which suits the sophistication already visible in your `scripts/` (typed shell harness,
  assertion functions). The parser _is_ the type.
- It's **1.x stable**, zero-dep core, dual ESM/CJS, and unusually well-tested (property-based).

The honest costs: the **parser-combinator paradigm has a real learning curve**, and Optique is **parsing-only** — it hands you
a fully-typed result and you write the command execution. For your scripts that's actually a _good_ fit: the orchestration logic
(release/push/clone) already exists; you mostly need typed parsing + help + validation wrapped around it (use `@optique/discover`
if you want turnkey multi-command dispatch). It's also primarily single-author — mitigated by the 1.0 milestone and test rigor.

**Strong runner-up: Stricli.** Pick it instead if you'd rather have a **conventional application framework** than learn
combinators. Its route-map model maps cleanly onto `repo-tools release | push | clone`, its **dependency-injection context** is
the best testability story of the four (and your scripts already pass a typed `$` harness around — that becomes the injected
context naturally), and **Bloomberg's governance** (OpenSSF Scorecard, DCO, conventional releases) is the most reassuring for a
dependency you'll standardize on across repos. The tradeoffs you'd accept: **no Zod adapter** (call Zod inside a custom `parse`
or in the handler — easy, just not first-class), **bash-only completion installer** today, and **no built-in env/config/prompt**
(you inject those through the context — which, given your enquirer plan and existing harness, you'd likely do anyway).

**Decision rule:**

- Want maximal type-safety + native Zod + batteries (env/config/prompt/completion) and OK learning combinators → **Optique**.
- Want turnkey routing + DI testability + a scaffolder + institutional backing, and fine calling Zod yourself → **Stricli**.

**On "replicating their core idea" instead of depending on one:** I'd advise against full replication for a _published_ toolset —
both finalists are 1.x, zero-dep, and maintained. Reinventing the parser is real maintenance you don't need. What _is_ worth
borrowing is an **architectural pattern**: Stricli's injected-context DI and Optique's `ValueParser` abstraction are both
small, clean ideas you could mirror in thin wrappers around whichever library you choose — that gives you portability without
owning a parser.

---

## Decision — Optique

Two requirements settled it:

1. **CLI value parsers should literally be Zod schemas → yes.** Only Optique does this first-class. `@optique/zod`'s
   `zod(schema, { placeholder })` returns a `ValueParser` you drop straight into `option()` / `argument()`; the schema's
   output type flows through Optique's inference into the final result type. It auto-infers the help metavar from the schema
   (`z.string().email()` → `EMAIL`, `z.coerce.number().int()` → `INTEGER`, `z.enum([...])` → `CHOICE`) and exposes
   `choices`/`suggest()` so Zod enums also drive shell completion. `zodAsync()` + `runAsync()` handles async refinements.
   Supports Zod v3.25+ and v4. Env/config fallbacks (`bindEnv()`/`bindConfig()`) are validated by the _same_ schema.
2. **zsh/fish completion (good to have) → yes.** Optique generates completion for **bash, zsh, fish, nushell, powershell**
   (`packages/core/src/completion.ts`), dependency-aware. Stricli's installer is bash-only today.

### Practical notes for adoption

- **Use `z.coerce` for non-string types.** CLI args are strings, so `z.coerce.number()`, not `z.number()`.
- **`placeholder` is required** in `zod()` options (a phase-one stand-in used during deferred prompt resolution).
- **`zod()` is sync; use `zodAsync()` + `runAsync()`** for schemas with async refinements/transforms.
- **Runtime fit:** `@optique/zod` declares `bun >= 1.2`, `node >= 20`, `deno >= 2.3`; Zod is a peer dependency.
- **Prompts:** you mentioned `enquirer`. Optique's bundled interactive fallback is `@optique/inquirer` (inquirer, not
  enquirer). You can still call `enquirer` yourself inside a handler; it's library-neutral. If you want Optique's built-in
  "ask when a value is missing" behavior specifically, that path uses inquirer.
- **Multi-command shape:** for `repo-tools release | push | clone`, model each as `command("release", object({...}))` combined
  with `or(...)`, tagging each with `constant("release")` for a discriminated-union result; or use `@optique/discover` for
  file-based command modules with handler dispatch.

### Runner-up note

Keep **Stricli** in mind only if the team later prefers a conventional app-framework (route maps + dependency-injection
context + scaffolder) over the combinator paradigm and is willing to call Zod manually and accept bash-only completion. Given
the two requirements above, Optique is the clear pick.
