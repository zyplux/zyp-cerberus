# Roadmap: renderer presets

Make React renderers first-class. `eslint-plugin-react`'s `recommended` set is
DOM-oriented, so its DOM-only rules (chiefly `react/no-unknown-property`) misfire
on non-DOM renderers — OpenTUI, Ink, react-three-fiber, react-pdf — whose host
elements carry props that are not DOM attributes. Today `react: true` applies one
DOM ruleset to every file and `nonDomReactFiles` subtracts a single rule as a
bolt-on. Replace both with a renderer-keyed map: one curated preset per renderer,
each scoped to its own globs.

Supersedes §2c of `battle-test-fixes-and-improvements.md`.

## API

`react` accepts a renderer → globs map; `react: true` stays as shorthand.

```ts
totvibe({
  react: {
    dom: ['apps/web/**/*.{ts,tsx}'], // full eslint-plugin-react (DOM)
    opentui: ['apps/tui/**/*.{ts,tsx}'], // react − DOM-only rules
    // r3f:  ['apps/scene/**/*.{ts,tsx}'],
  },
  reactVersion: '19.0',
  tsconfigRootDir: import.meta.dirname,
});

// react: true  ≡  { dom: ['**/src/**/*.{ts,tsx}'] }
```

Only listed globs receive React rules, so non-React packages match nothing — this
also retires the "React blankets every package" behavior of the old `reactFiles`
default.

## Presets

One flat-config block per renderer: shared base (React Hooks + `jsx-runtime` +
the renderer-agnostic React rules) plus a per-preset toggle of `domOnlyReactRules`.

- `dom` — DOM-only rules on (the current `recommended`).
- `opentui` / `ink` / `r3f` / `react-pdf` — DOM-only rules `off`.

`domOnlyReactRules` is at minimum `react/no-unknown-property`; audit and fold in
the other DOM-coupled members (`react/void-dom-elements-no-children`,
`react/no-danger-with-children`, `react/no-render-return-value`).

Non-DOM presets default to `off`, not an ignore-list: on a 100%-non-DOM element
the rule flags every non-DOM prop, so an ignore-list must enumerate nearly the
whole renderer prop surface and rots on each renderer release — while `tsc`
already validates the exact, complete prop type for free. Allow an opt-in
`{ ignore: string[] }` form per renderer for the mixed-DOM case (foreign props on
real DOM elements), where keeping DOM validation is worthwhile.

## Non-goals

- No custom lint rule that re-validates renderer props — `tsc` does this via
  `JSX.IntrinsicElements` with zero maintenance.
- No auto-detection of the renderer from each tsconfig's `jsxImportSource` —
  globs are explicit and self-documenting; keep the topology in the config, not
  inferred. A `renderersFromTsconfigs(root)` helper can come later as opt-in.

## Back-compat

Map the legacy options onto the new model and keep them working for one release:
`react: true` → `{ dom: reactFiles }`; `nonDomReactFiles` → `{ opentui }`. Update
the README options table and mark the flat options deprecated.
