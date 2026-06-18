# cerberus

Verifies repository invariants — CI workflows, branch-protection rulesets, CODEOWNERS, workflow secrets, and justfile conventions. Run it two ways: as a per-repo linter against a checkout (`cerberus`), or as a central scan across every repo in the org (`cerberus org`).

## Requirements

- [`uv`](https://docs.astral.sh/uv/) and Python 3.14
- [`just`](https://just.systems/) (the `justfile` check shells out to it)
- [`gh`](https://cli.github.com/), authenticated against the org — only for `cerberus org`

## Lint a repo

```sh
uv run cerberus            # lint the current directory
uv run cerberus PATH       # lint a checkout at PATH
```

Runs the content checks (`justfile`, `ci-workflow`, `codeowners`) against the checkout and exits non-zero when a check fails — errors fail, warnings do not — so it drops into CI like any linter. Control-plane checks (`ruleset`, `workflow-secrets`) read GitHub org/admin state the checkout cannot see, so they are skipped here and reported by `cerberus org`.

Run `cerberus list` to see every check, its scope, and what it verifies.

| Option          | Description                                  |
| --------------- | -------------------------------------------- |
| `--check NAME`  | Limit to named check(s); repeatable          |
| `--config PATH` | Use a `cerberus.toml` other than the bundled |
| `--json`        | Emit JSON instead of a table                 |
| `--fix`         | Auto-fix problems where possible (planned)   |

## Scan the org

`cerberus org` takes the org as a required argument — a bare name, `github.com/<org>`, or a full URL.

```sh
uv run cerberus org zyplux                  # every finding, per repo (default)
uv run cerberus org github.com/zyplux       # same, org given as a URL
uv run cerberus org zyplux scorecard        # cross-repo pass/fail matrix
uv run cerberus org zyplux repos            # list the repos cerberus governs
```

`scorecard` and the default view accept `--repo`/`-r`, `--check`, and `--json`, and run all checks including the control-plane ones. A failure exits non-zero (errors only).

## Checks

| ID                 | Scope         | Verifies                                             |
| ------------------ | ------------- | ---------------------------------------------------- |
| `justfile`         | content       | Uniform recipe names, aliases, and `check` pipeline  |
| `ci-workflow`      | content       | `ci.yml` exists, exposes a `ci` check, runs on PRs   |
| `codeowners`       | content       | `CODEOWNERS` present and covers `/.github/`          |
| `ruleset`          | control-plane | Default branch protected by the org baseline ruleset |
| `workflow-secrets` | control-plane | Every secret referenced in workflows is provisioned  |

## Config

Policy — org name, excluded repos, ruleset name, required recipes and aliases — lives in [`cerberus.toml`](src/cerberus/cerberus.toml). Override it with `--config PATH`.
