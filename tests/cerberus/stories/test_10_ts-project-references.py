from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from cerberus import config, context
from cerberus.checks import ts_project_references_check
from cerberus.model import CheckResult, Repo, Status

RunTsProjectReferences = Callable[[dict[str, str]], CheckResult]

_NON_WORKSPACE_PKG = '{"scripts": {"typecheck": "tsc -b"}}'
_NO_TSCONFIG_PKG = '{"workspaces": ["packages/*"], "scripts": {"typecheck": "tsc -b"}}'
_NO_TYPECHECK_PKG = '{"workspaces": ["packages/*"], "scripts": {"test": "vitest run"}}'
_TSC_P_PKG = '{"workspaces": ["packages/*"], "scripts": {"typecheck": "tsc --noEmit -p tsconfig.json"}}'
_FANOUT_PKG = '{"workspaces": ["packages/*"], "scripts": {"typecheck": "tsc -p . && bun --filter \'*\' typecheck"}}'
_TSB_PKG = '{"workspaces": ["packages/*"], "scripts": {"typecheck": "tsc -b"}}'
_TSBUILD_PKG = '{"workspaces": ["packages/*"], "scripts": {"typecheck": "tsc --build"}}'


@pytest.fixture
def repo() -> Repo:
    return Repo("demo")


@pytest.fixture
def ctx() -> context.Context:
    return context.local_context(config.load(), Path())


@pytest.fixture
def run_ts_project_references(
    monkeypatch: pytest.MonkeyPatch, repo: Repo, ctx: context.Context
) -> RunTsProjectReferences:
    def _run(files: dict[str, str]) -> CheckResult:
        monkeypatch.setattr(ctx, "paths", lambda _repo: sorted(files))
        monkeypatch.setattr(ctx, "file", lambda _repo, path: files.get(path))
        return ts_project_references_check.run(repo, ctx)

    return _run


def test_10_1_1_skips_repos_with_no_package_json(run_ts_project_references: RunTsProjectReferences) -> None:
    assert run_ts_project_references({"README.md": "# demo\n"}).status is Status.SKIP


def test_10_1_2_skips_repos_whose_package_json_is_not_a_workspace(
    run_ts_project_references: RunTsProjectReferences,
) -> None:
    files = {"package.json": _NON_WORKSPACE_PKG, "tsconfig.json": "{}"}
    assert run_ts_project_references(files).status is Status.SKIP


def test_10_1_3_skips_workspaces_with_no_tsconfig_file(run_ts_project_references: RunTsProjectReferences) -> None:
    assert run_ts_project_references({"package.json": _NO_TSCONFIG_PKG}).status is Status.SKIP


def test_10_2_1_fails_when_the_typecheck_script_is_missing(run_ts_project_references: RunTsProjectReferences) -> None:
    files = {"package.json": _NO_TYPECHECK_PKG, "tsconfig.json": "{}"}
    assert run_ts_project_references(files).status is Status.FAIL


def test_10_2_2_fails_when_the_typecheck_script_only_builds_a_single_project(
    run_ts_project_references: RunTsProjectReferences,
) -> None:
    files = {"package.json": _TSC_P_PKG, "tsconfig.json": "{}"}
    assert run_ts_project_references(files).status is Status.FAIL


def test_10_2_3_fails_when_the_typecheck_script_fans_out_per_package_via_bun_filter(
    run_ts_project_references: RunTsProjectReferences,
) -> None:
    files = {"package.json": _FANOUT_PKG, "tsconfig.json": "{}"}
    assert run_ts_project_references(files).status is Status.FAIL


@pytest.mark.parametrize("manifest", [_TSB_PKG, _TSBUILD_PKG], ids=["tsc -b", "tsc --build"])
def test_10_2_4_passes_when_the_typecheck_script_builds_via_project_references(
    run_ts_project_references: RunTsProjectReferences, manifest: str
) -> None:
    files = {"package.json": manifest, "tsconfig.json": "{}"}
    assert run_ts_project_references(files).status is Status.PASS
