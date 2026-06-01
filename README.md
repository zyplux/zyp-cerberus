# @totvibe/eslint-config

Shared ESLint flat config and custom rules for totvibe projects. Ships TypeScript source — consumed directly under Bun.

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
  react: true,
  tanstack: true,
  tsconfigRootDir: import.meta.dirname,
});
```

### Options

| Option            | Default                    | Description                                      |
| ----------------- | -------------------------- | ------------------------------------------------ |
| `react`           | `false`                    | Enable `eslint-plugin-react` + React Hooks rules |
| `tanstack`        | `false`                    | Enforce kebab-case filenames under `routes/`     |
| `tsconfigRootDir` | `process.cwd()`            | Root for typed linting (`projectService`)        |
| `reactFiles`      | `['**/src/**/*.{ts,tsx}']` | Globs the React rules apply to                   |
| `ignores`         | `[]`                       | Extra ignore globs appended to the defaults      |

The custom `@totvibe` rules (`no-inferrable-return-type`, `no-type-predicate`, `no-zod-custom`, `prefer-arrow-functions`) are bundled and always on.

## Develop

```sh
just install
just check
```

Individual recipes: `just lint`, `just typecheck`, `just test`, `just format`, `just knip`.

## Publish

```sh
just publish
```
