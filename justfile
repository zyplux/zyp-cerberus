set shell := ["bash", "-euo", "pipefail", "-c"]

alias i := install
alias k := knip
alias tc := typecheck
alias l := lint
alias t := test
alias c := check
alias u := upgrade
alias ui := upgrade-interactive

# List available recipes.
default:
    @just --list

# Install dependencies (the prepare script installs git hooks via lefthook).
install:
    bun install

# Report unused files, dependencies, and exports via knip.
knip:
    bun run knip

# Type-check root config files and all workspaces.
typecheck:
    bun run typecheck

# Lint and format with autofix: eslint --fix + prettier --write.
lint:
    bun run lint:fix
    bun run format

# Run all workspace tests.
test:
    bun run test

# Full gate: install, knip, typecheck, lint, test — autofix throughout.
check: install knip typecheck lint test

# Auto-format with prettier.
format:
    bun run format

# Upgrade JS dependencies across the workspace via ncu (catalog-aware). Forwards extra args (e.g. `just u -i`).
upgrade *args='':
    bun run upgrade -- {{ args }}

# Interactively select and apply upgrades, then reinstall.
upgrade-interactive:
    bun run upgrade -- -i
    bun install

# Cut a GitHub release for the current package version, then watch the publish workflow and verify it on npm.
release:
    bun run release

# Push the current branch and open a draft PR (-r/--ready marks it ready and enables auto-merge).
push *flags:
    bun run push -- {{ flags }}

# Remove dependencies and caches.
clean:
    rm -rf node_modules packages/*/node_modules tests/*/node_modules
