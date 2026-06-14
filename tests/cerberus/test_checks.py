import pytest
from cerberus import config, gh
from cerberus.checks import codeowners_check, justfile_check, secrets_check
from cerberus.context import Context
from cerberus.model import Repo, Status

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


@pytest.fixture
def repo():
    return Repo("demo", "zyplux", "main", "public", archived=False, is_fork=False)


@pytest.fixture
def ctx():
    return Context(config=config.load())


def test_conforming_justfile_passes(monkeypatch, repo, ctx):
    monkeypatch.setattr(gh, "raw_file", lambda *a: CONFORMING)
    assert justfile_check.run(repo, ctx).status is Status.PASS


def test_missing_justfile_fails(monkeypatch, repo, ctx):
    monkeypatch.setattr(gh, "raw_file", lambda *a: None)
    assert justfile_check.run(repo, ctx).status is Status.FAIL


def test_missing_required_alias_fails(monkeypatch, repo, ctx):
    monkeypatch.setattr(gh, "raw_file", lambda *a: MISSING_REQUIRED_ALIAS)
    assert justfile_check.run(repo, ctx).status is Status.FAIL


def test_missing_recommended_only_warns(monkeypatch, repo, ctx):
    monkeypatch.setattr(gh, "raw_file", lambda *a: MISSING_RECOMMENDED)
    assert justfile_check.run(repo, ctx).status is Status.WARN


def test_wrong_check_pipeline_order_fails(monkeypatch, repo, ctx):
    monkeypatch.setattr(gh, "raw_file", lambda *a: WRONG_CHECK_ORDER)
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
    monkeypatch.setattr(gh, "raw_file", lambda *a: None)
    assert codeowners_check.run(repo, ctx).status is Status.FAIL


def test_codeowners_covers_github(monkeypatch, repo, ctx):
    monkeypatch.setattr(gh, "raw_file", lambda owner, name, path: "/.github/ @zyplux/admins\n")
    assert codeowners_check.run(repo, ctx).status is Status.PASS
