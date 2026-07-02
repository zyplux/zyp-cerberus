from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from cerberus import config, context
from cerberus.checks import catalog_discipline_check
from cerberus.model import CheckResult, Finding, Repo, Status

RunCatalogDiscipline = Callable[[dict[str, str]], CheckResult]

_CATALOG_WS_ROOT = '{"workspaces": ["packages/*"], "devDependencies": {"eslint": "catalog:"}}'
_CATALOG_NON_WS = '{"dependencies": {"eslint": "^9.0.0"}}'
_CATALOG_PINNED_PKG = '{"dependencies": {"@zyplux/util": "workspace:*", "zod": "catalog:"}}'
_CATALOG_RAW_PKG = '{"dependencies": {"zod": "^3.0.0"}}'
_CATALOG_VENDORED_PKG = '{"dependencies": {"left-pad": "^1.0.0"}}'


@pytest.fixture
def repo() -> Repo:
    return Repo("demo")


@pytest.fixture
def ctx() -> context.Context:
    return context.local_context(config.load(), Path())


@pytest.fixture
def run_catalog_discipline(monkeypatch: pytest.MonkeyPatch, repo: Repo, ctx: context.Context) -> RunCatalogDiscipline:
    def run(files: dict[str, str]) -> CheckResult:
        monkeypatch.setattr(ctx, "paths", lambda _repo: sorted(files))
        monkeypatch.setattr(ctx, "file", lambda _repo, path: files.get(path))
        return catalog_discipline_check.run(repo, ctx)

    return run


def test_11_1_1_skips_repos_with_no_package_json(run_catalog_discipline: RunCatalogDiscipline) -> None:
    result = run_catalog_discipline({})
    assert result.findings == [Finding(Status.SKIP, "no package.json")]


def test_11_1_2_skips_repos_whose_package_json_is_not_a_workspace(
    run_catalog_discipline: RunCatalogDiscipline,
) -> None:
    result = run_catalog_discipline({"package.json": _CATALOG_NON_WS})
    assert result.findings == [Finding(Status.SKIP, "not a workspace")]


def test_11_2_1_passes_when_every_dependency_pins_via_catalog_or_workspace(
    run_catalog_discipline: RunCatalogDiscipline,
) -> None:
    result = run_catalog_discipline({"package.json": _CATALOG_WS_ROOT, "packages/a/package.json": _CATALOG_PINNED_PKG})
    assert result.findings == [Finding(Status.PASS, "every dependency uses catalog: or workspace:")]


def test_11_2_2_fails_and_names_the_dependency_that_pins_a_raw_version(
    run_catalog_discipline: RunCatalogDiscipline,
) -> None:
    result = run_catalog_discipline({"package.json": _CATALOG_WS_ROOT, "packages/a/package.json": _CATALOG_RAW_PKG})
    assert result.findings == [
        Finding(
            Status.FAIL,
            "dependency not pinned via catalog:/workspace: — packages/a/package.json → dependencies.zod = '^3.0.0'",
        )
    ]


def test_11_2_3_treats_an_unparseable_manifest_as_declaring_no_dependencies(
    run_catalog_discipline: RunCatalogDiscipline,
) -> None:
    result = run_catalog_discipline({"package.json": _CATALOG_WS_ROOT, "packages/a/package.json": "not json"})
    assert result.findings == [Finding(Status.PASS, "every dependency uses catalog: or workspace:")]


def test_11_3_1_ignores_dependencies_declared_in_a_vendored_node_modules_package_json(
    run_catalog_discipline: RunCatalogDiscipline,
) -> None:
    result = run_catalog_discipline({
        "package.json": _CATALOG_WS_ROOT,
        "node_modules/d/package.json": _CATALOG_VENDORED_PKG,
    })
    assert result.findings == [Finding(Status.PASS, "every dependency uses catalog: or workspace:")]
