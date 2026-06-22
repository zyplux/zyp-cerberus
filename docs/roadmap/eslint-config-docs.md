# Roadmap for eslint-config

## Generate docs from tests
- restructure tests into incorrect-correct pairs, mark if fixable
- for fixable pairs correct should be the outcome of the fix
- then for every pair for the rule generate markdown docs (viewable in GitHub, structure similar to unicorn/eslint-plugin-vitest etc.)
- run only for changed/new rule-tests, detect renames/deletions
- rule diagnostics should link to the rule docs
- ci test to try to regenerate the rules and ensure no diffs
