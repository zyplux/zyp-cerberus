# 1. [Requiring repos to ship a conformant justfile](test_1_justfile.py)

Every repo in the org must ship a `justfile` that gives contributors the same
commands everywhere: `install`, `lint`, `test`, `check`, and so on. The
`justfile` check (`apps/cerberus/src/cerberus/checks/justfile_check.py`)
enforces that shape, and it leans on the `justfile` module
(`apps/cerberus/src/cerberus/justfile.py`) to parse the file's aliases,
recipes, dependencies, and bodies via `just --dump`.

## 1.1 requiring a present, fully conforming justfile

A repo either has a justfile that satisfies every rule below, or the check
reports why it doesn't — starting with whether a justfile exists at all.

### 1.1.1 passes a fully conforming justfile

A justfile with every required and recommended alias, every required and
recommended recipe, a correctly ordered `check` pipeline, a `default` recipe
that lists available commands, and no bare managed tool calls or trailing
whitespace passes with no findings.

### 1.1.2 fails when the repo has no justfile at its root

When `ctx.file` returns no content for `justfile`, the check fails immediately
with a "no justfile at repo root" style finding and never attempts to parse
anything.

## 1.2 keeping aliases and recipes conformant

Every recipe needs a short alias (`i`, `k`, `tc`, `l`, `t`, `c`, plus the
recommended `u`/`ui`), and every pipeline recipe needs to exist under its own
name (`default`, `install`, `knip`, `typecheck`, `lint`, `test`, `check`, plus
the recommended `upgrade`, `upgrade-interactive`, `clean`). An alias that
exists but points at the wrong recipe is treated the same as a missing one.

### 1.2.1 fails when a required alias is missing or targets the wrong recipe

Dropping one of the required aliases (e.g. `alias k := knip`), or repointing
one at the wrong recipe (e.g. `alias k := lint`), fails the check.

### 1.2.2 fails when a required recipe is missing

Dropping one of the required recipes (e.g. the `default` or `lint` recipe)
from an otherwise conforming justfile fails the check.

### 1.2.3 fails when a recommended alias or recipe is missing

Dropping a recommended alias (e.g. `alias ui := upgrade-interactive`) or a
recommended recipe (e.g. the `clean` recipe) from an otherwise conforming
justfile fails the check.

## 1.3 ordering the check recipe pipeline

The `check` recipe's dependency list must run the configured pipeline steps
(`install`, `knip`, `typecheck`, `lint`, `test`) in order, though other steps
may be interleaved between them.

### 1.3.1 fails when the check recipe runs its steps out of order

Reordering the `check` recipe's dependencies (e.g. running `lint` before
`knip`/`typecheck`) so the required pipeline steps no longer appear in the
configured order fails the check.

### 1.3.2 determines whether one step list is an in order subsequence of another

The pipeline-order rule is backed by a general in-order-subsequence test:
a needle list matches a haystack list when every needle item appears in the
haystack in the same relative order, with other items allowed in between
(e.g. `["install", "knip", "test"]` in `["install", "build", "knip", "test"]`),
and fails to match when an item is out of order or absent entirely.

## 1.4 requiring the default recipe to list available commands

When a justfile defines a `default` recipe, its body must run the configured
discovery command (`just --list`) so that running bare `just` shows
contributors what's available, instead of silently doing something else.

### 1.4.1 fails when the default recipe does not list available commands

A `default` recipe whose body never calls `just --list` fails the check, even
when every other rule is satisfied.

## 1.5 requiring managed tools to run through their wrapper

Managed tools (`ruff`, `rumdl`, `pytest`, `eslint`, ...) must never be invoked
bare in a recipe body, because a bare call relies on an ambient install
instead of the project's `uv run`/`bunx` wrapper.

### 1.5.1 fails and names the tool when a recipe calls it directly

A recipe body that leads with a managed tool's own command (e.g. `lint:` running
`rumdl check` instead of `bun run lint`) fails the check, and the failure
message names the offending tool.

## 1.6 keeping recipe lines free of trailing whitespace

Recipe lines must not carry trailing spaces or tabs.

### 1.6.1 fails when a recipe line has trailing whitespace

A justfile whose otherwise-conforming `check` recipe line ends in trailing
spaces fails the check.

## 1.7 parsing justfile content into structured data

`justfile.parse` turns raw justfile text into structured aliases, recipes,
dependencies, and bodies by shelling out to `just --dump --dump-format json`.

### 1.7.1 extracts recipes aliases dependencies and bodies from justfile content

Parsing a justfile yields its aliases as a name-to-target mapping, each
recipe's dependencies as an ordered list, and each recipe's body text.

### 1.7.2 collapses interpolation fragments when extracting recipe bodies

A `just --dump` recipe body is a list of lines whose fragments can be nested
interpolation nodes rather than plain strings; parsing collapses each
interpolation fragment to a single space so the body still reads as text and
its recipe's dependency list still parses correctly.
