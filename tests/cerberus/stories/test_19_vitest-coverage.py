from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path

import pytest
from cerberus import config, context
from cerberus.checks import vitest_coverage_check
from cerberus.model import CheckResult, Repo, Status

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
    assert run_vitest_coverage({"README.md": "# demo\n"}).status is Status.SKIP


def test_19_1_2_ignores_a_nested_vitest_config_that_is_not_at_the_repo_root(
    run_vitest_coverage: RunVitestCoverage,
) -> None:
    files = {"packages/a/vitest.config.ts": "export default defineProject({ test: {} });\n"}

    assert run_vitest_coverage(files).status is Status.SKIP


def test_19_2_1_errors_when_the_root_vitest_config_cannot_be_read(run_vitest_coverage: RunVitestCoverage) -> None:
    result = run_vitest_coverage({"vitest.config.ts": None})

    assert result.status is Status.ERROR


def test_19_2_2_fails_when_the_coverage_block_is_unterminated(run_vitest_coverage: RunVitestCoverage) -> None:
    files = {"vitest.config.ts": "export default defineConfig({ test: { coverage: { thresholds: {\n"}

    result = run_vitest_coverage(files)

    assert result.status is Status.FAIL


def test_19_3_1_fails_when_the_config_has_no_coverage_block(run_vitest_coverage: RunVitestCoverage) -> None:
    files = {"vitest.config.ts": "export default defineConfig({ test: {} });\n"}

    assert run_vitest_coverage(files).status is Status.FAIL


def test_19_3_2_fails_when_the_coverage_block_has_no_thresholds(run_vitest_coverage: RunVitestCoverage) -> None:
    files = {"vitest.config.ts": "export default defineConfig({ test: { coverage: { provider: 'istanbul' } } });\n"}

    assert run_vitest_coverage(files).status is Status.FAIL


def test_19_4_1_fails_and_names_the_metric_when_a_threshold_is_below_the_required_floor(
    run_vitest_coverage: RunVitestCoverage,
) -> None:
    files = {"vitest.config.ts": _COMPLIANT_CONFIG.replace("branches: 90", "branches: 80")}

    result = run_vitest_coverage(files)

    assert result.status is Status.FAIL
    assert any("branches" in finding.message for finding in result.findings)


def test_19_4_2_fails_when_a_threshold_metric_is_missing(run_vitest_coverage: RunVitestCoverage) -> None:
    files = {"vitest.config.ts": _COMPLIANT_CONFIG.replace("branches: 90,\n", "")}

    result = run_vitest_coverage(files)

    assert result.status is Status.FAIL
    assert any("branches" in finding.message for finding in result.findings)


def test_19_5_1_passes_when_every_threshold_metric_meets_the_required_floor(
    run_vitest_coverage: RunVitestCoverage,
) -> None:
    assert run_vitest_coverage({"vitest.config.ts": _COMPLIANT_CONFIG}).status is Status.PASS
