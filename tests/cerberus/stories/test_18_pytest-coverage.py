from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from cerberus import config, context
from cerberus.checks import pytest_coverage_check
from cerberus.model import CheckResult, Finding, Repo, Status

RunPytestCoverage = Callable[[str | None], CheckResult]

_OK_MESSAGE = "pytest coverage gate enforces >= 90% ([tool.coverage.report] fail_under)"


@pytest.fixture
def repo() -> Repo:
    return Repo("demo")


@pytest.fixture
def ctx() -> context.Context:
    return context.local_context(config.load(), Path())


@pytest.fixture
def run_pytest_coverage(monkeypatch: pytest.MonkeyPatch, repo: Repo, ctx: context.Context) -> RunPytestCoverage:
    def run(pyproject: str | None) -> CheckResult:
        monkeypatch.setattr(ctx, "file", lambda _r, _p: pyproject)
        return pytest_coverage_check.run(repo, ctx)

    return run


def test_18_1_1_skips_repos_with_no_pyproject_file(run_pytest_coverage: RunPytestCoverage) -> None:
    result = run_pytest_coverage(None)

    assert result.findings == [Finding(Status.SKIP, "no pyproject.toml (not a Python repo)")]


def test_18_2_1_errors_when_pyproject_cannot_be_parsed(run_pytest_coverage: RunPytestCoverage) -> None:
    result = run_pytest_coverage("[project\nname = 'demo'\n")

    assert result.findings == [Finding(Status.ERROR, "could not parse pyproject.toml")]


def test_18_2_2_fails_when_there_is_no_tool_coverage_report_fail_under(
    run_pytest_coverage: RunPytestCoverage,
) -> None:
    result = run_pytest_coverage("[project]\nname = 'demo'\n")

    assert result.findings == [
        Finding(
            Status.FAIL,
            "pyproject.toml has no [tool.coverage.report] fail_under; "
            "pytest coverage must enforce a floor of at least 90%",
        )
    ]


def test_18_2_3_fails_when_fail_under_is_not_a_number(run_pytest_coverage: RunPytestCoverage) -> None:
    pyproject = "[project]\nname = 'demo'\n\n[tool.coverage.report]\nfail_under = 'ninety'\n"

    result = run_pytest_coverage(pyproject)

    assert result.findings == [
        Finding(Status.FAIL, "pyproject.toml [tool.coverage.report] fail_under must be a number; found 'ninety'")
    ]


def test_18_3_1_fails_when_fail_under_is_below_the_required_floor(run_pytest_coverage: RunPytestCoverage) -> None:
    pyproject = "[project]\nname = 'demo'\n\n[tool.coverage.report]\nfail_under = 80\n"

    result = run_pytest_coverage(pyproject)

    assert result.findings == [
        Finding(Status.FAIL, "pyproject.toml [tool.coverage.report] fail_under is 80, below the required 90")
    ]


@pytest.mark.parametrize("fail_under", [90, 95], ids=["at-floor", "above-floor"])
def test_18_3_2_passes_when_fail_under_meets_or_exceeds_the_required_floor(
    run_pytest_coverage: RunPytestCoverage, fail_under: int
) -> None:
    pyproject = f"[project]\nname = 'demo'\n\n[tool.coverage.report]\nfail_under = {fail_under}\n"

    result = run_pytest_coverage(pyproject)

    assert result.findings == [Finding(Status.PASS, _OK_MESSAGE)]
