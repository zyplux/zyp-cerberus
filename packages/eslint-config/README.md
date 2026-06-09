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

One call is the whole config: ESLint recommended, type-checked typescript-eslint, unicorn, perfectionist (natural sorting), the custom `@totvibe` rules, and prettier last. React is off until you ask for it.

## React renderers

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

- `dom` — DOM rules on (eslint-plugin-react `recommended` + `jsx-runtime` + React Hooks).
- `opentui` / `ink` / `r3f` / `react-pdf` — same, but `react/no-unknown-property` off, since `tsc` already validates each renderer's host props through `JSX.IntrinsicElements`.
- Shorthand: `react: true` ≡ `{ dom: ['**/src/**/*.{ts,tsx}'] }`.

## Monorepos

One `totvibe()` call with a renderer map covers a whole repo: set `tsconfigRootDir` once and `projectService` resolves each package's nearest `tsconfig.json`. When packages need genuinely different baselines, scope whole presets with `defineConfig` and share options through `withDefaults`:

```ts
import { defineConfig } from 'eslint/config';
import { totvibe } from '@totvibe/eslint-config';

const tv = totvibe.withDefaults({ tsconfigRootDir: import.meta.dirname });

export default defineConfig(
  { files: ['packages/api/**'], extends: [tv()] },
  { files: ['packages/web/**'], extends: [tv({ react: true })] },
);
```

## Options

| Option            | Default         | Description                                                             |
| ----------------- | --------------- | ----------------------------------------------------------------------- |
| `react`           | `false`         | `true`, or a renderer → globs map (see above)                           |
| `tanstack`        | `false`         | Enforce kebab-case filenames under `routes/`                            |
| `tsconfigRootDir` | `process.cwd()` | Root for typed linting (`projectService`); pin to `import.meta.dirname` |
| `reactVersion`    | `'detect'`      | React version; pin (e.g. `'19.0'`) where workspace detection fails      |
| `ignores`         | `[]`            | Extra ignore globs appended to the defaults                             |

Deprecated, mapped onto `react` for back-compat: `reactFiles` → `react: { dom }`, `nonDomReactFiles` → `react: { opentui }`.

## What's always on

- Custom `@totvibe` rules: `no-inferrable-return-type`, `no-type-predicate`, `no-zod-custom`, `prefer-arrow-functions`.
- Type-checked TypeScript (`strictTypeChecked` + `stylisticTypeChecked`), arrow-only functions, `type` over `interface`, no type assertions.
- No parent-relative (`../`) imports — route through a tsconfig `paths` alias (`@/foo`).
- unicorn + perfectionist (natural sorting); prettier last, so formatting rules are off.

## Tweaking rules

Flat config is last-wins — append an override after the preset:

```ts
export default [...totvibe({ tsconfigRootDir: import.meta.dirname }), { rules: { 'unicorn/no-null': 'off' } }];
```
