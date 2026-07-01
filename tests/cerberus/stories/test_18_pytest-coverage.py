from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from cerberus import config, context
from cerberus.checks import pytest_coverage_check
from cerberus.model import CheckResult, Repo, Status

RunPytestCoverage = Callable[..., CheckResult]

_COMPLIANT_PYPROJECT = "[project]\nname = 'demo'\n\n[tool.coverage.report]\nfail_under = 90\n"


@pytest.fixture
def repo() -> Repo:
    return Repo("demo")


@pytest.fixture
def ctx() -> context.Context:
    return context.local_context(config.load(), Path())


@pytest.fixture
def run_pytest_coverage(monkeypatch: pytest.MonkeyPatch, repo: Repo, ctx: context.Context) -> RunPytestCoverage:
    def run(*, pyproject: str | None = _COMPLIANT_PYPROJECT) -> CheckResult:
        monkeypatch.setattr(ctx, "file", lambda _r, _p: pyproject)
        return pytest_coverage_check.run(repo, ctx)

    return run


def test_18_1_1_skips_repos_with_no_pyproject_file(run_pytest_coverage: RunPytestCoverage) -> None:
    assert run_pytest_coverage(pyproject=None).status is Status.SKIP


def test_18_2_1_errors_when_pyproject_cannot_be_parsed(run_pytest_coverage: RunPytestCoverage) -> None:
    result = run_pytest_coverage(pyproject="[project\nname = 'demo'\n")

    assert result.status is Status.ERROR


def test_18_2_2_fails_when_there_is_no_tool_coverage_report_fail_under(
    run_pytest_coverage: RunPytestCoverage,
) -> None:
    result = run_pytest_coverage(pyproject="[project]\nname = 'demo'\n")

    assert result.status is Status.FAIL


def test_18_2_3_fails_when_fail_under_is_not_a_number(run_pytest_coverage: RunPytestCoverage) -> None:
    pyproject = "[project]\nname = 'demo'\n\n[tool.coverage.report]\nfail_under = 'ninety'\n"

    result = run_pytest_coverage(pyproject=pyproject)

    assert result.status is Status.FAIL


def test_18_3_1_fails_when_fail_under_is_below_the_required_floor(run_pytest_coverage: RunPytestCoverage) -> None:
    pyproject = "[project]\nname = 'demo'\n\n[tool.coverage.report]\nfail_under = 80\n"

    result = run_pytest_coverage(pyproject=pyproject)

    assert result.status is Status.FAIL


def test_18_3_2_passes_when_fail_under_meets_the_required_floor(run_pytest_coverage: RunPytestCoverage) -> None:
    assert run_pytest_coverage().status is Status.PASS


def test_18_3_3_passes_when_fail_under_exceeds_the_required_floor(run_pytest_coverage: RunPytestCoverage) -> None:
    pyproject = "[project]\nname = 'demo'\n\n[tool.coverage.report]\nfail_under = 95\n"

    result = run_pytest_coverage(pyproject=pyproject)

    assert result.status is Status.PASS
