from collections.abc import Callable
from pathlib import Path

import pytest
from cerberus import config, context
from cerberus.checks import codeowners_check
from cerberus.model import CheckResult, Finding, Repo, Status

FileReader = Callable[[Repo, str], str | None]

COVERS_GITHUB = "/.github/ @zyplux/admins\n"
WILDCARD_COVERS_EVERYTHING = "* @zyplux/admins\n"
LOOKALIKE_GITHUB_PATH = "docs/.github-notes @zyplux/admins\n"
NO_OWNERSHIP_RULES = "# just a header comment\n\n"


@pytest.fixture
def repo() -> Repo:
    return Repo("demo")


@pytest.fixture
def ctx() -> context.Context:
    return context.local_context(config.load(), Path())


@pytest.fixture
def run_codeowners(
    monkeypatch: pytest.MonkeyPatch, repo: Repo, ctx: context.Context
) -> Callable[[FileReader], CheckResult]:
    def run(reader: FileReader) -> CheckResult:
        monkeypatch.setattr(ctx, "file", reader)
        return codeowners_check.run(repo, ctx)

    return run


def test_2_1_1_fails_when_no_codeowners_file_exists_in_any_recognized_location(
    run_codeowners: Callable[[FileReader], CheckResult],
) -> None:
    result = run_codeowners(lambda *_: None)
    assert result.findings == [Finding(Status.FAIL, "no CODEOWNERS file")]


def test_2_1_2_passes_when_the_codeowners_file_exists_in_an_alternate_recognized_location(
    run_codeowners: Callable[[FileReader], CheckResult],
) -> None:
    result = run_codeowners(lambda _repo, path: COVERS_GITHUB if path == "docs/CODEOWNERS" else None)
    assert result.findings == [Finding(Status.PASS, "CODEOWNERS present, covers /.github/")]


def test_2_1_3_fails_when_the_codeowners_file_has_no_ownership_rules(
    run_codeowners: Callable[[FileReader], CheckResult],
) -> None:
    result = run_codeowners(lambda *_: NO_OWNERSHIP_RULES)
    assert result.findings == [Finding(Status.FAIL, "CODEOWNERS has no ownership rules")]


def test_2_2_1_passes_when_a_rule_explicitly_owns_the_github_directory(
    run_codeowners: Callable[[FileReader], CheckResult],
) -> None:
    result = run_codeowners(lambda *_: COVERS_GITHUB)
    assert result.findings == [Finding(Status.PASS, "CODEOWNERS present, covers /.github/")]


def test_2_2_2_passes_when_a_wildcard_rule_owns_everything(
    run_codeowners: Callable[[FileReader], CheckResult],
) -> None:
    result = run_codeowners(lambda *_: WILDCARD_COVERS_EVERYTHING)
    assert result.findings == [Finding(Status.PASS, "CODEOWNERS present, covers /.github/")]


def test_2_2_3_fails_when_only_a_lookalike_github_path_is_owned(
    run_codeowners: Callable[[FileReader], CheckResult],
) -> None:
    result = run_codeowners(lambda *_: LOOKALIKE_GITHUB_PATH)
    assert result.findings == [Finding(Status.FAIL, "CODEOWNERS does not cover `/.github/`")]
