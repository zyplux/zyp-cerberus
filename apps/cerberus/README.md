# cerberus

Verifies repository invariants — CI workflows, CODEOWNERS, workflow secrets, and justfile conventions. Run it two ways: as a per-repo linter against a checkout (`cerberus`), or as a central scan across every repo in the org (`cerberus org`).

## Requirements

- [`uv`](https://docs.astral.sh/uv/) and Python 3.14
- [`gh`](https://cli.github.com/), authenticated against the org — only for `cerberus org`

The `justfile` check shells out to `just`, which ships with the package (via [`rust-just`](https://pypi.org/project/rust-just/)) — no separate install.

## Lint a repo

```sh
uv run cerberus            # lint the current directory
uv run cerberus PATH       # lint a checkout at PATH
```

Runs the content checks (`justfile`, `ci-workflow`, `codeowners`) against the checkout and exits non-zero on any failure or error, so it drops into CI like any linter. Control-plane checks (`workflow-secrets`) read GitHub org/admin state the checkout cannot see, so they are skipped here and reported by `cerberus org`.

Run `cerberus list` to see every check, its scope, and what it verifies.

| Option          | Description                                          |
| --------------- | ---------------------------------------------------- |
| `--check NAME`  | Limit to named check(s); repeatable                  |
| `--config PATH` | Use a `cerberus.toml` other than the bundled         |
| `--fix`         | Auto-fix fixable problems (e.g. trailing whitespace) |

## Scan the org

`cerberus org` takes the org as a required argument — a bare name, `github.com/<org>`, or a full URL.

```sh
uv run cerberus org zyplux                  # scan every repo, report findings
uv run cerberus org github.com/zyplux       # same, org given as a URL
uv run cerberus org zyplux --repo api       # scan only the named repo(s)
```

Runs all checks, including the control-plane ones the local linter skips. Accepts `--repo`/`-r` and `--check`. A failure or error exits non-zero.

## Checks

| ID                 | Scope         | Verifies                                                                            |
| ------------------ | ------------- | ----------------------------------------------------------------------------------- |
| `justfile`         | content       | Recipe names, aliases, `check` pipeline, wrapped tool calls, no trailing whitespace |
| `ci-workflow`      | content       | `ci.yml` exists, exposes a `ci` check, runs on PRs                                  |
| `workflow-tooling` | content       | Workflows set up only the workspace toolchain (uv, bun), not extra tools            |
| `codeowners`       | content       | `CODEOWNERS` present and covers `/.github/`                                         |
| `workflow-secrets` | control-plane | Every secret referenced in workflows is provisioned                                 |

## Config

Policy — org name, excluded repos, required recipes and aliases — lives in [`cerberus.toml`](src/cerberus/cerberus.toml). Override it with `--config PATH`.
