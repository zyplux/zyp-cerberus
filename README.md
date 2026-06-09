# @totvibe/eslint-config

Shared ESLint flat config and custom rules. Ships TypeScript source — consumed directly under Bun.

## Install

```sh
bun add -D @totvibe/eslint-config eslint typescript
```

## Use

`eslint.config.ts`:

```ts
import { totvibe } from '@totvibe/eslint-config';

export default totvibe({ tsconfigRootDir: import.meta.dirname });
```

Frontend (React + TanStack Router):

```ts
import { totvibe } from '@totvibe/eslint-config';

export default totvibe({
  react: true, // ≡ { dom: ['**/src/**/*.{ts,tsx}'] }
  tanstack: true,
  tsconfigRootDir: import.meta.dirname,
});
```

### React renderers

`react` takes a renderer → globs map. Only listed globs receive React rules, so non-React packages match nothing.

```ts
export default totvibe({
  react: {
    dom: ['apps/web/**/*.{ts,tsx}'], // full eslint-plugin-react (DOM)
    opentui: ['apps/tui/**/*.{ts,tsx}'], // non-DOM renderer
  },
  reactVersion: '19.0',
  tsconfigRootDir: import.meta.dirname,
});
```

`dom` keeps DOM rules on; the non-DOM renderers `opentui`, `ink`, `r3f`, `react-pdf` turn off `react/no-unknown-property`, because `tsc` already validates each renderer's host props through `JSX.IntrinsicElements` (no ignore-list to maintain). All renderers share the React Hooks + `jsx-runtime` base.

### Monorepos

A single `totvibe()` call with a renderer map covers a whole repo: set `tsconfigRootDir` once and `projectService` resolves each package's nearest `tsconfig.json`. When packages need genuinely different baselines, scope whole presets with `defineConfig` and share options through `withDefaults`:

```ts
import { defineConfig } from 'eslint/config';
import { totvibe } from '@totvibe/eslint-config';

const tv = totvibe.withDefaults({ tsconfigRootDir: import.meta.dirname });

export default defineConfig(
  { files: ['packages/api/**'], extends: [tv()] },
  { files: ['packages/web/**'], extends: [tv({ react: true })] },
);
```

### Options

| Option            | Default         | Description                                                                           |
| ----------------- | --------------- | ------------------------------------------------------------------------------------- |
| `react`           | `false`         | `true`, or a renderer → globs map (`dom` / `opentui` / `ink` / `r3f` / `react-pdf`)   |
| `tanstack`        | `false`         | Enforce kebab-case filenames under `routes/`                                          |
| `tsconfigRootDir` | `process.cwd()` | Root for typed linting (`projectService`)                                             |
| `reactVersion`    | `'detect'`      | React version for `eslint-plugin-react`; pin it (e.g. `'19.0'`) where detection fails |
| `ignores`         | `[]`            | Extra ignore globs appended to the defaults                                           |

`reactVersion` matters in a workspace where `react` is a per-app dependency: `'detect'` resolves from the lint working directory, finds nothing at the monorepo root, warns, and falls back nondeterministically — pin the version to silence it.

Deprecated, kept working for back-compat: `reactFiles` maps onto `react: { dom }` and `nonDomReactFiles` onto `react: { opentui }` (the latter still requires React enabled).

The custom `@totvibe` rules (`no-identity-cast`, `no-inferrable-return-type`, `no-type-predicate`, `no-zod-custom`, `prefer-arrow-functions`) are bundled and always on.

### No parent-relative imports

`../`-style imports are banned (`@typescript-eslint/no-restricted-imports`, every depth including `import type`). Route intra-package references through a tsconfig `paths` alias so moving a file never breaks them:

```json
{
  "compilerOptions": {
    "paths": { "@/*": ["./src/*"] }
  }
}
```

`import { x } from '@/foo'` then resolves from any depth, with one wildcard. TypeScript (5+, no `baseUrl`) and Bun read `paths` natively; Vite does not — add [`vite-tsconfig-paths`](https://github.com/aleclarson/vite-tsconfig-paths) so tsconfig stays the single source of truth. Cross-package references go through the workspace package name (`@scope/pkg`).

### zod at the boundary

`consistent-type-assertions: 'never'` plus `no-zod-custom` and `no-type-predicate` steer every deserialization boundary (`JSON.parse`, `event.data`, JSONL) toward a zod schema that _returns_ the typed value rather than `parse(x) as T`. Annotate hand-written schemas as `z.ZodType<T>` to keep their declared type. Blind spot: that annotation only rejects schemas producing values _outside_ `T` — a schema _missing_ a union member still type-checks (the narrower output is assignable to the wider `T`), so a discriminated union can silently drop a case. Keep wire schemas exhaustive by hand.

## Develop

```sh
just install
just check
```

Individual recipes: `just lint`, `just typecheck`, `just test`, `just format`, `just knip`.

## Publish

```sh
just release
```
