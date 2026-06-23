# @zyplux/tsconfig

Shared TypeScript configs for the zyplux org. Project-reference ready — `composite`, declaration-only emit to a throwaway `.tsbuild/`, run with `tsc -b`.

## Use

`tsconfig.json`:

```jsonc
{ "extends": "@zyplux/tsconfig/bun.json", "include": ["src"] }
```

Variants, all extending `base`:

| Variant | Environment                          |
| ------- | ------------------------------------ |
| `bun`   | Bun / Node                           |
| `web`   | browser + React DOM                  |
| `tui`   | terminal React (`@opentui/react`)    |
| `iso`   | none — isomorphic, no env globals    |

`base` is abstract; extend a variant, not `base`. Add `.tsbuild/` to `.gitignore`.
