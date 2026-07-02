from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path

import pytest
from cerberus import config, context
from cerberus.checks import vitest_coverage_check
from cerberus.model import CheckResult, Finding, Repo, Status

RunVitestCoverage = Callable[[Mapping[str, str | None]], CheckResult]

_COMPLIANT_CONFIG = (
    "export default defineConfig({\n"
    "  test: {\n"
    "    coverage: {\n"
    "      thresholds: {\n"
    "        branches: 90,\n"
    "        functions: 90,\n"
    "        lines: 90,\n"
    "        statements: 90,\n"
    "      },\n"
    "    },\n"
    "  },\n"
    "});\n"
)

_SKIP_FINDING = Finding(Status.SKIP, "no root vitest.config")
_NO_COVERAGE_FINDING = Finding(
    Status.FAIL,
    "vitest.config.ts has no `coverage` block; vitest coverage must enforce a floor of at least 90%",
)


@pytest.fixture
def repo() -> Repo:
    return Repo("demo")


@pytest.fixture
def ctx() -> context.Context:
    return context.local_context(config.load(), Path())


@pytest.fixture
def run_vitest_coverage(monkeypatch: pytest.MonkeyPatch, repo: Repo, ctx: context.Context) -> RunVitestCoverage:
    def _run(files: Mapping[str, str | None]) -> CheckResult:
        monkeypatch.setattr(ctx, "paths", lambda _repo: sorted(files))
        monkeypatch.setattr(ctx, "file", lambda _repo, path: files.get(path))
        return vitest_coverage_check.run(repo, ctx)

    return _run


def test_19_1_1_skips_repos_with_no_root_vitest_config(run_vitest_coverage: RunVitestCoverage) -> None:
    result = run_vitest_coverage({"README.md": "# demo\n"})

    assert result.findings == [_SKIP_FINDING]


def test_19_1_2_ignores_a_nested_vitest_config_that_is_not_at_the_repo_root(
    run_vitest_coverage: RunVitestCoverage,
) -> None:
    files = {"packages/a/vitest.config.ts": "export default defineProject({ test: {} });\n"}

    result = run_vitest_coverage(files)

    assert result.findings == [_SKIP_FINDING]


def test_19_2_1_errors_when_the_root_vitest_config_cannot_be_read(run_vitest_coverage: RunVitestCoverage) -> None:
    result = run_vitest_coverage({"vitest.config.ts": None})

    assert result.findings == [Finding(Status.ERROR, "could not read vitest.config.ts")]


def test_19_2_2_fails_when_the_coverage_block_is_unterminated(run_vitest_coverage: RunVitestCoverage) -> None:
    files = {"vitest.config.ts": "export default defineConfig({ test: { coverage: { thresholds: {\n"}

    result = run_vitest_coverage(files)

    assert result.findings == [_NO_COVERAGE_FINDING]


def test_19_3_1_fails_when_the_config_has_no_coverage_block(run_vitest_coverage: RunVitestCoverage) -> None:
    files = {"vitest.config.ts": "export default defineConfig({ test: {} });\n"}

    result = run_vitest_coverage(files)

    assert result.findings == [_NO_COVERAGE_FINDING]


def test_19_3_2_fails_when_the_coverage_block_has_no_thresholds(run_vitest_coverage: RunVitestCoverage) -> None:
    files = {"vitest.config.ts": "export default defineConfig({ test: { coverage: { provider: 'istanbul' } } });\n"}

    result = run_vitest_coverage(files)

    assert result.findings == [
        Finding(
            Status.FAIL,
            "vitest.config.ts `coverage` has no `thresholds`; "
            "must set branches/functions/lines/statements to at least 90",
        )
    ]


def test_19_4_1_fails_and_names_the_metric_when_a_threshold_is_below_the_required_floor(
    run_vitest_coverage: RunVitestCoverage,
) -> None:
    files = {"vitest.config.ts": _COMPLIANT_CONFIG.replace("branches: 90", "branches: 80")}

    result = run_vitest_coverage(files)

    assert result.findings == [
        Finding(Status.FAIL, "vitest.config.ts coverage.thresholds.branches is 80.0, below the required 90")
    ]


def test_19_4_2_fails_when_a_threshold_metric_is_missing(run_vitest_coverage: RunVitestCoverage) -> None:
    files = {"vitest.config.ts": _COMPLIANT_CONFIG.replace("branches: 90,\n", "")}

    result = run_vitest_coverage(files)

    assert result.findings == [
        Finding(Status.FAIL, "vitest.config.ts coverage.thresholds has no `branches`; must be set to at least 90")
    ]


def test_19_5_1_passes_when_every_threshold_metric_meets_the_required_floor(
    run_vitest_coverage: RunVitestCoverage,
) -> None:
    result = run_vitest_coverage({"vitest.config.ts": _COMPLIANT_CONFIG})

    assert result.findings == [Finding(Status.PASS, "vitest coverage gate enforces >= 90% (coverage.thresholds)")]
