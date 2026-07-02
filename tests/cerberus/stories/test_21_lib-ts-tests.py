from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from cerberus import config, context
from cerberus.checks import lib_ts_tests_check
from cerberus.model import CheckResult, Finding, Repo, Status

RunLibTsTests = Callable[[dict[str, str]], CheckResult]

_SEAM_ROOT_WS = '{"workspaces": ["apps/*", "packages/*", "tests/*"]}'
_SEAM_LIB = (
    '{"name": "@demo/lib",'
    ' "exports": {".": {"types": "./src/index.ts", "default": "./src/index.ts"},'
    ' "./package.json": "./package.json"}}'
)
_SEAM_LIB_NO_EXPORTS = '{"name": "@demo/lib"}'
_SEAM_LIB_LEAKY = '{"name": "@demo/lib", "exports": {".": "./src/index.ts", "./helpers": "./src/helpers.ts"}}'
_SEAM_LIB_NO_ROOT = '{"name": "@demo/lib", "exports": {"./package.json": "./package.json"}}'
_SEAM_LIB_CONDITIONS = '{"name": "@demo/lib", "exports": {"types": "./src/index.ts", "default": "./src/index.ts"}}'
_SEAM_JSON_ONLY = '{"name": "@demo/tsconfig"}'
_SEAM_CLI_LEAKY = (
    '{"name": "@demo/cli", "bin": {"cli": "./src/index.ts"},'
    ' "exports": {".": "./src/cli.ts", "./commands/deps-catalog": "./src/commands/deps-catalog.ts"}}'
)
_SEAM_FIXTURES_LIB_LEAKY = (
    '{"name": "@demo/tests-fixtures", "exports": {".": "./src/index.ts", "./story": "./src/story.ts"}}'
)
_SEAM_TESTS_PKG = '{"name": "@demo/tests-lib", "private": true, "imports": {"#fixtures": "./fixtures.ts"}}'
_SEAM_TESTS_PKG_LEAKY_EXPORTS = (
    '{"name": "@demo/tests-lib", "private": true, "exports": {"./internal": "./internal.ts"},'
    ' "imports": {"#fixtures": "./fixtures.ts"}}'
)
_SEAM_TESTS_PKG_SNEAKY = (
    '{"name": "@demo/tests-lib", "private": true,'
    ' "imports": {"#fixtures": "./fixtures.ts", "#sneaky": "../../packages/lib/src/internal.ts"}}'
)
_SEAM_CLEAN_STORY = "import path from 'node:path';\n\nimport { describe, expect, test } from '#fixtures';\n"
_SEAM_LIB_IMPORT_STORY = "import { helper } from '@demo/lib';\n\nimport { test } from '#fixtures';\n"
_SEAM_RELATIVE_ESCAPE_STORY = (
    "import { internal } from '../../../packages/lib/src/internal.ts';\n\nimport { test } from '#fixtures';\n"
)
_SEAM_THIRD_PARTY_STORY = "import * as z from 'zod';\n\nimport { test } from '#fixtures';\n"
_SEAM_OTHER_LIB = '{"name": "@demo/other", "exports": {".": "./src/index.ts", "./package.json": "./package.json"}}'
_SEAM_SIBLING_IMPORT_STORY = "import { internal } from '@demo/other/internal';\n\nimport { test } from '#fixtures';\n"

_SEAM_OK = "every library exports only the root seam; story tests reach workspace code only through fixture aliases"


@pytest.fixture
def repo() -> Repo:
    return Repo("demo")


@pytest.fixture
def ctx() -> context.Context:
    return context.local_context(config.load(), Path())


@pytest.fixture
def run_lib_ts_tests(monkeypatch: pytest.MonkeyPatch, repo: Repo, ctx: context.Context) -> RunLibTsTests:
    def run(files: dict[str, str]) -> CheckResult:
        monkeypatch.setattr(ctx, "paths", lambda _repo: sorted(files))
        monkeypatch.setattr(ctx, "file", lambda _repo, path: files.get(path))
        return lib_ts_tests_check.run(repo, ctx)

    return run


def test_21_1_1_skips_repos_with_no_typescript_packages(run_lib_ts_tests: RunLibTsTests) -> None:
    result = run_lib_ts_tests({})
    assert result.findings == [Finding(Status.SKIP, "no TypeScript packages")]


def test_21_1_2_skips_workspaces_with_no_library(run_lib_ts_tests: RunLibTsTests) -> None:
    result = run_lib_ts_tests({
        "package.json": _SEAM_ROOT_WS,
        "apps/cli/package.json": _SEAM_CLI_LEAKY,
        "apps/cli/src/index.ts": "",
    })
    assert result.findings == [Finding(Status.SKIP, "no libraries")]


def test_21_1_3_leaves_a_published_package_without_typescript_sources_unchecked(
    run_lib_ts_tests: RunLibTsTests,
) -> None:
    result = run_lib_ts_tests({
        "package.json": _SEAM_ROOT_WS,
        "packages/lib/package.json": _SEAM_LIB,
        "packages/lib/src/index.ts": "",
        "packages/tsconfig/package.json": _SEAM_JSON_ONLY,
        "packages/tsconfig/base.json": "{}",
    })
    assert result.findings == [Finding(Status.PASS, _SEAM_OK)]


def test_21_1_4_leaves_a_private_test_package_unchecked(run_lib_ts_tests: RunLibTsTests) -> None:
    result = run_lib_ts_tests({
        "package.json": _SEAM_ROOT_WS,
        "packages/lib/package.json": _SEAM_LIB,
        "packages/lib/src/index.ts": "",
        "tests/lib/package.json": _SEAM_TESTS_PKG_LEAKY_EXPORTS,
        "tests/lib/fixtures.ts": "",
    })
    assert result.findings == [Finding(Status.PASS, _SEAM_OK)]


def test_21_1_5_leaves_a_cli_app_to_the_cli_seam_check(run_lib_ts_tests: RunLibTsTests) -> None:
    result = run_lib_ts_tests({
        "package.json": _SEAM_ROOT_WS,
        "apps/cli/package.json": _SEAM_CLI_LEAKY,
        "apps/cli/src/index.ts": "",
        "packages/lib/package.json": _SEAM_LIB,
        "packages/lib/src/index.ts": "",
    })
    assert result.findings == [Finding(Status.PASS, _SEAM_OK)]


def test_21_2_1_passes_a_library_that_exports_only_the_root_seam(run_lib_ts_tests: RunLibTsTests) -> None:
    result = run_lib_ts_tests({
        "package.json": _SEAM_ROOT_WS,
        "packages/lib/package.json": _SEAM_LIB,
        "packages/lib/src/index.ts": "",
    })
    assert result.findings == [Finding(Status.PASS, _SEAM_OK)]


def test_21_2_2_fails_a_library_that_declares_no_exports(run_lib_ts_tests: RunLibTsTests) -> None:
    result = run_lib_ts_tests({
        "package.json": _SEAM_ROOT_WS,
        "packages/lib/package.json": _SEAM_LIB_NO_EXPORTS,
        "packages/lib/src/index.ts": "",
    })
    assert result.findings == [
        Finding(
            Status.FAIL,
            "packages/lib/package.json: library must declare exports; without one every internal module is importable",
        )
    ]


def test_21_2_3_fails_and_names_each_export_beyond_the_root_seam(run_lib_ts_tests: RunLibTsTests) -> None:
    result = run_lib_ts_tests({
        "package.json": _SEAM_ROOT_WS,
        "packages/lib/package.json": _SEAM_LIB_LEAKY,
        "packages/lib/src/index.ts": "",
    })
    assert result.findings == [
        Finding(
            Status.FAIL,
            "packages/lib/package.json: library exports expose more than the root seam — './helpers'",
        )
    ]


def test_21_2_4_fails_a_library_whose_exports_omit_the_root_entry(run_lib_ts_tests: RunLibTsTests) -> None:
    result = run_lib_ts_tests({
        "package.json": _SEAM_ROOT_WS,
        "packages/lib/package.json": _SEAM_LIB_NO_ROOT,
        "packages/lib/src/index.ts": "",
    })
    assert result.findings == [
        Finding(Status.FAIL, "packages/lib/package.json: library exports must include the '.' root seam")
    ]


def test_21_2_5_accepts_a_conditions_object_as_the_root_seam(run_lib_ts_tests: RunLibTsTests) -> None:
    result = run_lib_ts_tests({
        "package.json": _SEAM_ROOT_WS,
        "packages/lib/package.json": _SEAM_LIB_CONDITIONS,
        "packages/lib/src/index.ts": "",
    })
    assert result.findings == [Finding(Status.PASS, _SEAM_OK)]


def test_21_2_6_covers_a_published_library_under_the_tests_directory(run_lib_ts_tests: RunLibTsTests) -> None:
    result = run_lib_ts_tests({
        "package.json": _SEAM_ROOT_WS,
        "tests/fixtures/package.json": _SEAM_FIXTURES_LIB_LEAKY,
        "tests/fixtures/src/index.ts": "",
    })
    assert result.findings == [
        Finding(
            Status.FAIL,
            "tests/fixtures/package.json: library exports expose more than the root seam — './story'",
        )
    ]


def test_21_3_1_passes_story_tests_importing_only_fixture_aliases_and_node_builtins(
    run_lib_ts_tests: RunLibTsTests,
) -> None:
    result = run_lib_ts_tests({
        "package.json": _SEAM_ROOT_WS,
        "packages/lib/package.json": _SEAM_LIB,
        "packages/lib/src/index.ts": "",
        "tests/lib/package.json": _SEAM_TESTS_PKG,
        "tests/lib/stories/1-first.test.ts": _SEAM_CLEAN_STORY,
    })
    assert result.findings == [Finding(Status.PASS, _SEAM_OK)]


def test_21_3_2_fails_a_story_test_importing_the_library_directly(run_lib_ts_tests: RunLibTsTests) -> None:
    result = run_lib_ts_tests({
        "package.json": _SEAM_ROOT_WS,
        "packages/lib/package.json": _SEAM_LIB,
        "packages/lib/src/index.ts": "",
        "tests/lib/package.json": _SEAM_TESTS_PKG,
        "tests/lib/stories/1-first.test.ts": _SEAM_LIB_IMPORT_STORY,
    })
    assert result.findings == [
        Finding(
            Status.FAIL,
            "tests/lib/stories/1-first.test.ts: story test imports outside the fixtures seam — '@demo/lib'",
        )
    ]


def test_21_3_3_fails_a_story_test_reaching_into_library_internals_via_a_relative_path(
    run_lib_ts_tests: RunLibTsTests,
) -> None:
    result = run_lib_ts_tests({
        "package.json": _SEAM_ROOT_WS,
        "packages/lib/package.json": _SEAM_LIB,
        "packages/lib/src/index.ts": "",
        "tests/lib/package.json": _SEAM_TESTS_PKG,
        "tests/lib/stories/1-first.test.ts": _SEAM_RELATIVE_ESCAPE_STORY,
    })
    assert result.findings == [
        Finding(
            Status.FAIL,
            "tests/lib/stories/1-first.test.ts: story test imports outside the fixtures seam — "
            "'../../../packages/lib/src/internal.ts'",
        )
    ]


def test_21_3_4_allows_a_story_test_to_import_a_third_party_module_directly(
    run_lib_ts_tests: RunLibTsTests,
) -> None:
    result = run_lib_ts_tests({
        "package.json": _SEAM_ROOT_WS,
        "packages/lib/package.json": _SEAM_LIB,
        "packages/lib/src/index.ts": "",
        "tests/lib/package.json": _SEAM_TESTS_PKG,
        "tests/lib/stories/1-first.test.ts": _SEAM_THIRD_PARTY_STORY,
    })
    assert result.findings == [Finding(Status.PASS, _SEAM_OK)]


def test_21_3_5_fails_a_story_test_importing_a_sibling_workspace_package(run_lib_ts_tests: RunLibTsTests) -> None:
    result = run_lib_ts_tests({
        "package.json": _SEAM_ROOT_WS,
        "packages/lib/package.json": _SEAM_LIB,
        "packages/lib/src/index.ts": "",
        "packages/other/package.json": _SEAM_OTHER_LIB,
        "packages/other/src/index.ts": "",
        "tests/lib/package.json": _SEAM_TESTS_PKG,
        "tests/lib/stories/1-first.test.ts": _SEAM_SIBLING_IMPORT_STORY,
    })
    assert result.findings == [
        Finding(
            Status.FAIL,
            "tests/lib/stories/1-first.test.ts: story test imports outside the fixtures seam — '@demo/other/internal'",
        )
    ]


def test_21_4_1_fails_an_imports_alias_that_escapes_the_test_package(run_lib_ts_tests: RunLibTsTests) -> None:
    result = run_lib_ts_tests({
        "package.json": _SEAM_ROOT_WS,
        "packages/lib/package.json": _SEAM_LIB,
        "packages/lib/src/index.ts": "",
        "tests/lib/package.json": _SEAM_TESTS_PKG_SNEAKY,
        "tests/lib/stories/1-first.test.ts": _SEAM_CLEAN_STORY,
    })
    assert result.findings == [
        Finding(
            Status.FAIL,
            "tests/lib/package.json: imports alias escapes the test package — "
            "'#sneaky' -> '../../packages/lib/src/internal.ts'",
        )
    ]
