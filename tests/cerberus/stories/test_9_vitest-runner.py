from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from cerberus import config, context
from cerberus.checks import vitest_runner_check
from cerberus.model import CheckResult, Repo, Status

RunVitestRunner = Callable[[dict[str, str]], CheckResult]

_VITEST_PKG = '{"scripts": {"test": "vitest run"}}'
_BUN_TEST_PKG = '{"scripts": {"test": "bun test"}}'
_BUN_FILTER_PKG = '{"scripts": {"test": "bun --filter \'*\' test"}}'
_BUN_RUN_PKG = '{"scripts": {"test": "bun run test"}}'
_VITEST_IMPORT = "import { describe, expect, it } from 'vitest';\n"
_BUN_TEST_IMPORT = "import { describe, expect, it } from 'bun:test';\n"


@pytest.fixture
def repo() -> Repo:
    return Repo("demo")


@pytest.fixture
def ctx() -> context.Context:
    return context.local_context(config.load(), Path())


@pytest.fixture
def run_vitest_runner(monkeypatch: pytest.MonkeyPatch, repo: Repo, ctx: context.Context) -> RunVitestRunner:
    def _run(files: dict[str, str]) -> CheckResult:
        monkeypatch.setattr(ctx, "paths", lambda _repo: sorted(files))
        monkeypatch.setattr(ctx, "file", lambda _repo, path: files.get(path))
        return vitest_runner_check.run(repo, ctx)

    return _run


def test_9_1_1_skips_repos_with_no_package_json(run_vitest_runner: RunVitestRunner) -> None:
    assert run_vitest_runner({"README.md": "# demo\n"}).status is Status.SKIP


def test_9_2_1_fails_when_the_test_script_runs_bun_test_directly(run_vitest_runner: RunVitestRunner) -> None:
    files = {"package.json": _BUN_TEST_PKG, "src/a.test.ts": _VITEST_IMPORT}
    assert run_vitest_runner(files).status is Status.FAIL


def test_9_2_2_allows_a_bun_filter_script(run_vitest_runner: RunVitestRunner) -> None:
    files = {"package.json": _BUN_FILTER_PKG, "src/a.test.ts": _VITEST_IMPORT}
    assert run_vitest_runner(files).status is Status.PASS


def test_9_2_3_allows_a_bun_run_test_script(run_vitest_runner: RunVitestRunner) -> None:
    assert run_vitest_runner({"package.json": _BUN_RUN_PKG}).status is Status.PASS


def test_9_3_1_fails_when_a_test_file_imports_from_bun_test(run_vitest_runner: RunVitestRunner) -> None:
    files = {"package.json": _VITEST_PKG, "src/a.test.ts": _BUN_TEST_IMPORT}
    assert run_vitest_runner(files).status is Status.FAIL


def test_9_3_2_ignores_bun_test_imports_inside_vendored_node_modules_files(run_vitest_runner: RunVitestRunner) -> None:
    files = {"package.json": _VITEST_PKG, "node_modules/dep/x.test.ts": _BUN_TEST_IMPORT}
    assert run_vitest_runner(files).status is Status.PASS


def test_9_4_1_passes_when_the_test_script_and_test_files_both_use_vitest(run_vitest_runner: RunVitestRunner) -> None:
    files = {"package.json": _VITEST_PKG, "src/a.test.ts": _VITEST_IMPORT}
    assert run_vitest_runner(files).status is Status.PASS
