import shutil

import pytest
from cerberus import config, context, gh
from cerberus.checks import (
    ci_workflow_check,
    codeowners_check,
    justfile_check,
    ruleset_check,
    secrets_check,
    workflow_tooling_check,
)
from cerberus.model import Repo, Status

requires_just = pytest.mark.skipif(
    shutil.which("just") is None, reason="requires the `just` binary on PATH"
)

CONFORMING = """
alias i := install
alias k := knip
alias tc := typecheck
alias l := lint
alias t := test
alias c := check
alias u := upgrade
alias ui := upgrade-interactive

default:
    @just --list
install:
    bun install
knip:
    bun run knip
typecheck:
    bun run typecheck
lint:
    bun run lint
test:
    bun run test
check: install knip typecheck lint test
upgrade:
    bun run upgrade
upgrade-interactive:
    bun run upgrade -- -i
clean:
    rm -rf node_modules
"""

MISSING_REQUIRED_ALIAS = CONFORMING.replace("alias k := knip\n", "")
MISSING_RECOMMENDED = CONFORMING.replace("alias ui := upgrade-interactive\n", "").replace(
    "clean:\n    rm -rf node_modules\n", ""
)
WRONG_CHECK_ORDER = CONFORMING.replace(
    "check: install knip typecheck lint test", "check: install lint knip typecheck test"
)
BARE_TOOL_CALL = CONFORMING.replace("lint:\n    bun run lint\n", "lint:\n    rumdl check\n")
TRAILING_WHITESPACE = CONFORMING.replace(
    "check: install knip typecheck lint test\n",
    "check: install knip typecheck lint test   \n",
)


@pytest.fixture
def repo():
    return Repo("demo", "zyplux", "main", "public")


@pytest.fixture
def ctx():
    return context.github_context(config.load())


@requires_just
def test_conforming_justfile_passes(monkeypatch, repo, ctx):
    monkeypatch.setattr(gh, "raw_file", lambda *_: CONFORMING)
    assert justfile_check.run(repo, ctx).status is Status.PASS


def test_missing_justfile_fails(monkeypatch, repo, ctx):
    monkeypatch.setattr(gh, "raw_file", lambda *_: None)
    assert justfile_check.run(repo, ctx).status is Status.FAIL


@requires_just
def test_missing_required_alias_fails(monkeypatch, repo, ctx):
    monkeypatch.setattr(gh, "raw_file", lambda *_: MISSING_REQUIRED_ALIAS)
    assert justfile_check.run(repo, ctx).status is Status.FAIL


@requires_just
def test_missing_recommended_only_warns(monkeypatch, repo, ctx):
    monkeypatch.setattr(gh, "raw_file", lambda *_: MISSING_RECOMMENDED)
    assert justfile_check.run(repo, ctx).status is Status.WARN


@requires_just
def test_wrong_check_pipeline_order_fails(monkeypatch, repo, ctx):
    monkeypatch.setattr(gh, "raw_file", lambda *_: WRONG_CHECK_ORDER)
    assert justfile_check.run(repo, ctx).status is Status.FAIL


@requires_just
def test_bare_managed_tool_fails(monkeypatch, repo, ctx):
    monkeypatch.setattr(gh, "raw_file", lambda *_: BARE_TOOL_CALL)
    result = justfile_check.run(repo, ctx)
    assert result.status is Status.FAIL
    assert any("rumdl" in f.message for f in result.problems)


@requires_just
def test_trailing_whitespace_fails(monkeypatch, repo, ctx):
    monkeypatch.setattr(gh, "raw_file", lambda *_: TRAILING_WHITESPACE)
    assert justfile_check.run(repo, ctx).status is Status.FAIL


def test_secrets_skips_without_workflows(monkeypatch, repo, ctx):
    monkeypatch.setattr(ctx, "workflows", lambda r: {})
    assert secrets_check.run(repo, ctx).status is Status.SKIP


def test_secrets_pass_when_provisioned(monkeypatch, repo, ctx):
    monkeypatch.setattr(ctx, "workflows", lambda r: {"ci.yml": "x: ${{ secrets.FOO }}"})
    monkeypatch.setattr(ctx, "secret_available", lambda r, name: True)
    assert secrets_check.run(repo, ctx).status is Status.PASS


def test_secrets_fail_when_missing(monkeypatch, repo, ctx):
    monkeypatch.setattr(ctx, "workflows", lambda r: {"ci.yml": "x: ${{ secrets.FOO }}"})
    monkeypatch.setattr(ctx, "secret_available", lambda r, name: False)
    assert secrets_check.run(repo, ctx).status is Status.FAIL


def test_secrets_ignores_github_token(monkeypatch, repo, ctx):
    monkeypatch.setattr(ctx, "workflows", lambda r: {"ci.yml": "x: ${{ secrets.GITHUB_TOKEN }}"})
    monkeypatch.setattr(ctx, "secret_available", lambda r, name: False)
    assert secrets_check.run(repo, ctx).status is Status.PASS


def test_codeowners_missing_fails(monkeypatch, repo, ctx):
    monkeypatch.setattr(gh, "raw_file", lambda *_: None)
    assert codeowners_check.run(repo, ctx).status is Status.FAIL


def test_codeowners_covers_github(monkeypatch, repo, ctx):
    monkeypatch.setattr(gh, "raw_file", lambda owner, name, path: "/.github/ @zyplux/admins\n")
    assert codeowners_check.run(repo, ctx).status is Status.PASS


def test_codeowners_wildcard_covers_github(monkeypatch, repo, ctx):
    monkeypatch.setattr(gh, "raw_file", lambda *_: "* @zyplux/admins\n")
    assert codeowners_check.run(repo, ctx).status is Status.PASS


def test_codeowners_lookalike_path_does_not_cover_github(monkeypatch, repo, ctx):
    monkeypatch.setattr(gh, "raw_file", lambda *_: "docs/.github-notes @zyplux/admins\n")
    assert codeowners_check.run(repo, ctx).status is Status.WARN


def _ci_workflow(content):
    return lambda r, p: content if p.endswith((".yml", ".yaml")) else None


def test_ci_workflow_missing_fails(monkeypatch, repo, ctx):
    monkeypatch.setattr(ctx, "file", lambda r, p: None)
    assert ci_workflow_check.run(repo, ctx).status is Status.FAIL


def test_ci_workflow_invalid_yaml_errors(monkeypatch, repo, ctx):
    monkeypatch.setattr(ctx, "file", _ci_workflow("a: [unterminated"))
    assert ci_workflow_check.run(repo, ctx).status is Status.ERROR


def test_ci_workflow_non_mapping_errors(monkeypatch, repo, ctx):
    monkeypatch.setattr(ctx, "file", _ci_workflow("- just\n- a\n- list\n"))
    assert ci_workflow_check.run(repo, ctx).status is Status.ERROR


def test_ci_workflow_missing_ci_job_fails(monkeypatch, repo, ctx):
    monkeypatch.setattr(
        ctx, "file", _ci_workflow("on: [pull_request, push]\njobs:\n  build:\n    name: build\n")
    )
    assert ci_workflow_check.run(repo, ctx).status is Status.FAIL


def test_ci_workflow_missing_pull_request_fails(monkeypatch, repo, ctx):
    monkeypatch.setattr(ctx, "file", _ci_workflow("on: push\njobs:\n  ci:\n    name: ci\n"))
    assert ci_workflow_check.run(repo, ctx).status is Status.FAIL


def test_ci_workflow_missing_push_warns(monkeypatch, repo, ctx):
    monkeypatch.setattr(ctx, "file", _ci_workflow("on: pull_request\njobs:\n  ci:\n    name: ci\n"))
    assert ci_workflow_check.run(repo, ctx).status is Status.WARN


def test_ci_workflow_on_as_pyyaml_bool_key(monkeypatch, repo, ctx):
    # Bare `on:` parses to the Python key True, not the string "on".
    monkeypatch.setattr(
        ctx, "file", _ci_workflow("on:\n  pull_request:\n  push:\njobs:\n  ci:\n    name: ci\n")
    )
    assert ci_workflow_check.run(repo, ctx).status is Status.PASS


def test_ci_workflow_job_id_named_ci_passes(monkeypatch, repo, ctx):
    monkeypatch.setattr(
        ctx, "file", _ci_workflow("on: [pull_request, push]\njobs:\n  ci:\n    runs-on: x\n")
    )
    assert ci_workflow_check.run(repo, ctx).status is Status.PASS


_CLEAN_WORKFLOW = (
    "jobs:\n"
    "  ci:\n"
    "    steps:\n"
    "      - uses: actions/checkout@v6\n"
    "      - uses: astral-sh/setup-uv@v8.2.0\n"
    "      - uses: oven-sh/setup-bun@v2\n"
    "      - run: uv sync --locked\n"
    "      - run: bun install --frozen-lockfile\n"
)


def test_workflow_tooling_passes_on_workspace_toolchain(monkeypatch, repo, ctx):
    monkeypatch.setattr(ctx, "workflows", lambda r: {"ci.yml": _CLEAN_WORKFLOW})
    assert workflow_tooling_check.run(repo, ctx).status is Status.PASS


def test_workflow_tooling_skips_without_workflows(monkeypatch, repo, ctx):
    monkeypatch.setattr(ctx, "workflows", lambda r: {})
    assert workflow_tooling_check.run(repo, ctx).status is Status.SKIP


def test_workflow_tooling_flags_setup_node(monkeypatch, repo, ctx):
    wf = "jobs:\n  ci:\n    steps:\n      - uses: actions/setup-node@v4\n"
    monkeypatch.setattr(ctx, "workflows", lambda r: {"ci.yml": wf})
    assert workflow_tooling_check.run(repo, ctx).status is Status.FAIL


def test_workflow_tooling_flags_install_action(monkeypatch, repo, ctx):
    wf = "jobs:\n  ci:\n    steps:\n      - uses: taiki-e/install-action@just\n"
    monkeypatch.setattr(ctx, "workflows", lambda r: {"ci.yml": wf})
    assert workflow_tooling_check.run(repo, ctx).status is Status.FAIL


def test_workflow_tooling_flags_apt_install(monkeypatch, repo, ctx):
    wf = "jobs:\n  ci:\n    steps:\n      - run: sudo apt-get install -y just\n"
    monkeypatch.setattr(ctx, "workflows", lambda r: {"ci.yml": wf})
    assert workflow_tooling_check.run(repo, ctx).status is Status.FAIL


def test_workflow_tooling_allows_npm_publish(monkeypatch, repo, ctx):
    wf = "jobs:\n  ci:\n    steps:\n      - run: npm publish ./*.tgz --access public\n"
    monkeypatch.setattr(ctx, "workflows", lambda r: {"ci.yml": wf})
    assert workflow_tooling_check.run(repo, ctx).status is Status.PASS


def _ruleset(*rules):
    return list(rules)


def _pr_rule(reviews=1, code_owners=True):
    return {
        "type": "pull_request",
        "parameters": {
            "required_approving_review_count": reviews,
            "require_code_owner_review": code_owners,
        },
    }


def _status_checks_rule(*contexts):
    return {
        "type": "required_status_checks",
        "parameters": {"required_status_checks": [{"context": c} for c in contexts]},
    }


_GUARD_RULES = (
    {"type": "required_linear_history"},
    {"type": "non_fast_forward"},
    {"type": "deletion"},
)


def _baseline_rules():
    return _ruleset(_pr_rule(), _status_checks_rule("ci"), *_GUARD_RULES)


def _wire_ruleset(monkeypatch, ctx, *, active=True, rules=None):
    monkeypatch.setattr(ctx, "ruleset_active", lambda name: active)
    monkeypatch.setattr(ctx, "branch_rules", lambda r: rules if rules is not None else [])


def test_ruleset_baseline_passes(monkeypatch, repo, ctx):
    _wire_ruleset(monkeypatch, ctx, rules=_baseline_rules())
    assert ruleset_check.run(repo, ctx).status is Status.PASS


def test_ruleset_inactive_fails(monkeypatch, repo, ctx):
    _wire_ruleset(monkeypatch, ctx, active=False, rules=_baseline_rules())
    assert ruleset_check.run(repo, ctx).status is Status.FAIL


def test_ruleset_missing_pull_request_fails(monkeypatch, repo, ctx):
    _wire_ruleset(monkeypatch, ctx, rules=_ruleset(_status_checks_rule("ci"), *_GUARD_RULES))
    assert ruleset_check.run(repo, ctx).status is Status.FAIL


def test_ruleset_too_few_reviews_fails(monkeypatch, repo, ctx):
    rules = _ruleset(_pr_rule(reviews=0), _status_checks_rule("ci"), *_GUARD_RULES)
    _wire_ruleset(monkeypatch, ctx, rules=rules)
    assert ruleset_check.run(repo, ctx).status is Status.FAIL


def test_ruleset_missing_code_owner_review_warns(monkeypatch, repo, ctx):
    rules = _ruleset(_pr_rule(code_owners=False), _status_checks_rule("ci"), *_GUARD_RULES)
    _wire_ruleset(monkeypatch, ctx, rules=rules)
    assert ruleset_check.run(repo, ctx).status is Status.WARN


def test_ruleset_missing_status_checks_fails(monkeypatch, repo, ctx):
    _wire_ruleset(monkeypatch, ctx, rules=_ruleset(_pr_rule(), *_GUARD_RULES))
    assert ruleset_check.run(repo, ctx).status is Status.FAIL


def test_ruleset_missing_ci_context_fails(monkeypatch, repo, ctx):
    rules = _ruleset(_pr_rule(), _status_checks_rule("build"), *_GUARD_RULES)
    _wire_ruleset(monkeypatch, ctx, rules=rules)
    assert ruleset_check.run(repo, ctx).status is Status.FAIL


def test_ruleset_missing_guards_warn(monkeypatch, repo, ctx):
    _wire_ruleset(monkeypatch, ctx, rules=_ruleset(_pr_rule(), _status_checks_rule("ci")))
    assert ruleset_check.run(repo, ctx).status is Status.WARN
