from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

import pytest
from cerberus import config, context
from cerberus.checks import story_docs, story_tests_py_check, story_tests_ts_check
from cerberus.model import CheckResult, Finding, Repo, Status

RunFn = Callable[[Repo, context.Context], CheckResult]
RunStoryCheck = Callable[[RunFn, dict[str, str]], CheckResult]

DOC = (
    "# 1. Configuring a widget\n"
    "\n"
    "## 1.1 Widget setup\n"
    "\n"
    "### 1.1.1 shows the widget name\n"
    "\n"
    "### 1.1.2 accepts a custom color\n"
)
DOC_PATH = "tests/stories/1_widget.md"

PY_TEST_PATH = "tests/stories/test_1_widget.py"
PY_TEST = "def test_1_1_1_shows_the_widget_name():\n    pass\n\n\ndef test_1_1_2_accepts_a_custom_color():\n    pass\n"

TS_TEST_PATH = "tests/stories/1_widget.test.ts"
TS_TEST = "test('1.1.1 shows the widget name', () => {});\ntest('1.1.2 accepts a custom color', () => {});\n"

_PY_PLAIN_PYPROJECT = '[project]\nname = "widget"\n'
_PY_SCRIPTS_PYPROJECT = '[project]\nname = "widget"\n\n[project.scripts]\nwidget = "widget.cli:main"\n'
_PY_UV_WORKSPACE_APPS = '[tool.uv.workspace]\nmembers = ["apps/*"]\n'
_PY_UV_WORKSPACE_SERVICES = '[tool.uv.workspace]\nmembers = ["services/*"]\n'

_TS_PLAIN_PKG = '{"name": "widget"}'
_TS_BIN_PKG = '{"name": "widget", "bin": {"widget": "./src/index.ts"}}'
_TS_BUN_WORKSPACE_APPS = '{"workspaces": ["apps/*"]}'
_TS_BUN_WORKSPACE_WITH_TESTS_MEMBER = '{"workspaces": ["apps/*", "tests"]}'

OK_MESSAGE = "every story criterion has a matching, title-matched test"
NO_MATCHING_TEST_HEADER_MESSAGE = "tests/stories: story-doc ### header(s) with no matching test: 1.1.2"
STALE_LINK_MESSAGE = "tests/stories/1_widget.md: story header links are stale; run with --fix"
TITLE_DRIFT_MESSAGE = (
    "tests/stories: header/test title drift for 1.1.1 — header='shows the widget name' test='shows a different name'"
)


def _needs_story_tests_message(package: str) -> str:
    return f"{package}: exposes a public interface but has no tests/**/stories/*.md user-story tests"


NEEDS_STORY_TESTS_MESSAGE = _needs_story_tests_message(".")


def _linked(target: str) -> str:
    return DOC.replace("# 1. Configuring a widget\n", f"# 1. [Configuring a widget]({target})\n")


@pytest.fixture
def repo() -> Repo:
    return Repo("demo")


@pytest.fixture
def ctx() -> context.Context:
    return context.local_context(config.load(), Path())


@pytest.fixture
def run_story_check(monkeypatch: pytest.MonkeyPatch, repo: Repo, ctx: context.Context) -> RunStoryCheck:
    def _run(check: RunFn, files: dict[str, str]) -> CheckResult:
        monkeypatch.setattr(ctx, "paths", lambda _repo: sorted(files))
        monkeypatch.setattr(ctx, "file", lambda _repo, path: files.get(path))
        return check(repo, ctx)

    return _run


def test_15_1_1_skips_a_repo_with_no_python_packages_at_all(run_story_check: RunStoryCheck) -> None:
    result = run_story_check(story_tests_py_check.run, {"README.md": "# demo\n"})
    assert result.findings == [Finding(Status.SKIP, "no Python packages")]


def test_15_1_2_skips_a_repo_with_no_typescript_packages_at_all(run_story_check: RunStoryCheck) -> None:
    result = run_story_check(story_tests_ts_check.run, {"README.md": "# demo\n"})
    assert result.findings == [Finding(Status.SKIP, "no TypeScript packages")]


def test_15_1_3_ignores_a_directory_outside_the_workspace_glob(run_story_check: RunStoryCheck) -> None:
    files = {"pyproject.toml": _PY_UV_WORKSPACE_APPS, "libs/other/pyproject.toml": _PY_SCRIPTS_PYPROJECT}
    result = run_story_check(story_tests_py_check.run, files)
    assert result.findings == [Finding(Status.SKIP, "no Python packages")]


def test_15_1_4_excludes_the_top_level_tests_directory_from_being_treated_as_a_package(
    run_story_check: RunStoryCheck,
) -> None:
    files = {
        "package.json": _TS_BUN_WORKSPACE_WITH_TESTS_MEMBER,
        "tests/package.json": '{"name": "test-harness"}',
        "tests/some.test.ts": "test('does nothing special', () => {});\n",
    }
    result = run_story_check(story_tests_ts_check.run, files)
    assert result.findings == [Finding(Status.SKIP, "no TypeScript packages")]


def test_15_1_5_treats_a_nested_tests_directory_as_excluded_but_still_checks_its_sibling_package(
    run_story_check: RunStoryCheck,
) -> None:
    files = {
        "package.json": '{"workspaces": ["apps/*", "tests/*"]}',
        "apps/cz/package.json": _TS_BIN_PKG,
        "tests/cz/package.json": '{"name": "test-harness-cz"}',
    }
    result = run_story_check(story_tests_ts_check.run, files)
    assert result.findings == [Finding(Status.FAIL, _needs_story_tests_message("apps/cz"))]


def test_15_2_1_fails_a_python_package_that_exposes_a_cli_script_but_has_no_story_tests(
    run_story_check: RunStoryCheck,
) -> None:
    result = run_story_check(story_tests_py_check.run, {"pyproject.toml": _PY_SCRIPTS_PYPROJECT})
    assert result.findings == [Finding(Status.FAIL, NEEDS_STORY_TESTS_MESSAGE)]


def test_15_2_2_fails_a_typescript_package_that_exposes_a_bin_entry_but_has_no_story_tests(
    run_story_check: RunStoryCheck,
) -> None:
    result = run_story_check(story_tests_ts_check.run, {"package.json": _TS_BIN_PKG})
    assert result.findings == [Finding(Status.FAIL, NEEDS_STORY_TESTS_MESSAGE)]


def test_15_2_3_skips_a_python_package_with_no_public_interface_and_no_tests(run_story_check: RunStoryCheck) -> None:
    result = run_story_check(story_tests_py_check.run, {"pyproject.toml": _PY_PLAIN_PYPROJECT})
    assert result.findings == [Finding(Status.SKIP, "no Python package needs story-based tests")]


def test_15_2_4_skips_a_typescript_package_with_no_public_interface_and_no_tests(
    run_story_check: RunStoryCheck,
) -> None:
    result = run_story_check(story_tests_ts_check.run, {"package.json": _TS_PLAIN_PKG})
    assert result.findings == [Finding(Status.SKIP, "no TypeScript package needs story-based tests")]


def test_15_2_5_fails_a_python_package_that_already_has_plain_tests_but_no_story_docs(
    run_story_check: RunStoryCheck,
) -> None:
    files = {"pyproject.toml": _PY_PLAIN_PYPROJECT, "tests/test_widget.py": "def test_it():\n    pass\n"}
    result = run_story_check(story_tests_py_check.run, files)
    assert result.findings == [Finding(Status.FAIL, NEEDS_STORY_TESTS_MESSAGE)]


def test_15_2_6_fails_a_typescript_package_that_already_has_plain_tests_but_no_story_docs(
    run_story_check: RunStoryCheck,
) -> None:
    files = {"package.json": _TS_PLAIN_PKG, "tests/widget.test.ts": "test('does a thing', () => {});\n"}
    result = run_story_check(story_tests_ts_check.run, files)
    assert result.findings == [Finding(Status.FAIL, NEEDS_STORY_TESTS_MESSAGE)]


def test_15_3_1_passes_a_python_workspace_member_with_colocated_story_tests(run_story_check: RunStoryCheck) -> None:
    files = {
        "pyproject.toml": _PY_UV_WORKSPACE_APPS,
        "apps/widget/pyproject.toml": _PY_SCRIPTS_PYPROJECT,
        "apps/widget/tests/stories/1_widget.md": _linked("test_1_widget.py"),
        "apps/widget/tests/stories/test_1_widget.py": PY_TEST,
    }
    result = run_story_check(story_tests_py_check.run, files)
    assert result.findings == [Finding(Status.PASS, OK_MESSAGE)]


def test_15_3_2_passes_a_typescript_workspace_member_with_colocated_story_tests(
    run_story_check: RunStoryCheck,
) -> None:
    files = {
        "package.json": _TS_BUN_WORKSPACE_APPS,
        "apps/widget/package.json": _TS_BIN_PKG,
        "apps/widget/tests/stories/1_widget.md": _linked("1_widget.test.ts"),
        "apps/widget/tests/stories/1_widget.test.ts": TS_TEST,
    }
    result = run_story_check(story_tests_ts_check.run, files)
    assert result.findings == [Finding(Status.PASS, OK_MESSAGE)]


@pytest.mark.parametrize(
    ("check", "files"),
    [
        (
            story_tests_py_check.run,
            {
                "pyproject.toml": _PY_UV_WORKSPACE_APPS,
                "apps/widget/pyproject.toml": _PY_SCRIPTS_PYPROJECT,
                "tests/widget/stories/1_widget.md": _linked("test_1_widget.py"),
                "tests/widget/stories/test_1_widget.py": PY_TEST,
            },
        ),
        (
            story_tests_ts_check.run,
            {
                "package.json": _TS_BUN_WORKSPACE_APPS,
                "apps/widget/package.json": _TS_BIN_PKG,
                "tests/widget/stories/1_widget.md": _linked("1_widget.test.ts"),
                "tests/widget/stories/1_widget.test.ts": TS_TEST,
            },
        ),
    ],
    ids=["python", "typescript"],
)
def test_15_3_3_passes_a_workspace_member_whose_story_tests_are_torn_out_to_a_top_level_tests_directory(
    run_story_check: RunStoryCheck, check: RunFn, files: dict[str, str]
) -> None:
    result = run_story_check(check, files)
    assert result.findings == [Finding(Status.PASS, OK_MESSAGE)]


@pytest.mark.parametrize(
    ("check", "files"),
    [
        (
            story_tests_py_check.run,
            {
                "pyproject.toml": _PY_PLAIN_PYPROJECT,
                DOC_PATH: DOC,
                PY_TEST_PATH: "def test_1_1_1_shows_the_widget_name():\n    pass\n",
            },
        ),
        (
            story_tests_ts_check.run,
            {
                "package.json": _TS_PLAIN_PKG,
                DOC_PATH: DOC,
                TS_TEST_PATH: "test('1.1.1 shows the widget name', () => {});\n",
            },
        ),
    ],
    ids=["python", "typescript"],
)
def test_15_4_1_flags_a_story_header_with_no_matching_test(
    run_story_check: RunStoryCheck, check: RunFn, files: dict[str, str]
) -> None:
    result = run_story_check(check, files)
    assert result.findings == [
        Finding(Status.FAIL, NO_MATCHING_TEST_HEADER_MESSAGE),
        Finding(Status.FAIL, STALE_LINK_MESSAGE),
    ]


def test_15_4_2_flags_a_test_with_no_matching_story_header(run_story_check: RunStoryCheck) -> None:
    files = {
        "pyproject.toml": _PY_PLAIN_PYPROJECT,
        DOC_PATH: "# 1. Configuring a widget\n\n### 1.1.1 shows the widget name\n",
        PY_TEST_PATH: PY_TEST,
    }
    result = run_story_check(story_tests_py_check.run, files)
    assert result.findings == [
        Finding(Status.FAIL, "tests/stories: story test(s) with no matching ### header: 1.1.2"),
        Finding(Status.FAIL, STALE_LINK_MESSAGE),
    ]


@pytest.mark.parametrize(
    ("check", "files"),
    [
        (
            story_tests_py_check.run,
            {
                "pyproject.toml": _PY_PLAIN_PYPROJECT,
                DOC_PATH: DOC,
                PY_TEST_PATH: PY_TEST.replace("shows_the_widget_name", "shows_a_different_name"),
            },
        ),
        (
            story_tests_ts_check.run,
            {
                "package.json": _TS_PLAIN_PKG,
                DOC_PATH: DOC,
                TS_TEST_PATH: TS_TEST.replace("shows the widget name", "shows a different name"),
            },
        ),
    ],
    ids=["python", "typescript"],
)
def test_15_4_3_flags_a_title_that_has_drifted_between_the_header_and_its_test(
    run_story_check: RunStoryCheck, check: RunFn, files: dict[str, str]
) -> None:
    result = run_story_check(check, files)
    assert result.findings == [
        Finding(Status.FAIL, TITLE_DRIFT_MESSAGE),
        Finding(Status.FAIL, STALE_LINK_MESSAGE),
    ]


def test_15_4_4_flags_a_criterion_filed_under_the_wrong_section_doc(run_story_check: RunStoryCheck) -> None:
    files = {
        "pyproject.toml": _PY_PLAIN_PYPROJECT,
        DOC_PATH: DOC.replace("### 1.1.2", "### 2.1.2"),
        PY_TEST_PATH: PY_TEST.replace("test_1_1_2", "test_2_1_2"),
    }
    result = run_story_check(story_tests_py_check.run, files)
    assert result.findings == [
        Finding(Status.FAIL, "tests/stories/1_widget.md: story header(s) filed in the wrong section doc: 2.1.2"),
        Finding(Status.FAIL, STALE_LINK_MESSAGE),
    ]


def test_15_5_1_flags_a_stale_header_link(run_story_check: RunStoryCheck) -> None:
    files = {
        "pyproject.toml": _PY_PLAIN_PYPROJECT,
        DOC_PATH: DOC.replace("# 1. Configuring a widget\n", "# 1. [Configuring a widget](test_wrong_file.py)\n"),
        PY_TEST_PATH: PY_TEST,
    }
    result = run_story_check(story_tests_py_check.run, files)
    assert result.findings == [Finding(Status.FAIL, STALE_LINK_MESSAGE)]


class StaleLinkCase(NamedTuple):
    manifest_name: str
    manifest_content: str
    test_name: str
    test_content: str
    linked_target: str
    check: RunFn


_STALE_LINK_CASES = [
    StaleLinkCase(
        "pyproject.toml", _PY_PLAIN_PYPROJECT, "test_1_widget.py", PY_TEST, "test_1_widget.py", story_tests_py_check.run
    ),
    StaleLinkCase(
        "package.json", _TS_PLAIN_PKG, "1_widget.test.ts", TS_TEST, "1_widget.test.ts", story_tests_ts_check.run
    ),
]


@pytest.mark.parametrize("case", _STALE_LINK_CASES, ids=["python", "typescript"])
def test_15_5_2_rewrites_a_stale_header_link_and_passes_on_the_next_run(tmp_path: Path, case: StaleLinkCase) -> None:
    (tmp_path / case.manifest_name).write_text(case.manifest_content)
    stories = tmp_path / "tests" / "stories"
    stories.mkdir(parents=True)
    doc_path = stories / "1_widget.md"
    doc_path.write_text(DOC)
    (stories / case.test_name).write_text(case.test_content)

    fixer = context.local_context(config.load(), tmp_path, fix=True)
    case.check(fixer.repos()[0], fixer)
    assert f"[Configuring a widget]({case.linked_target})" in doc_path.read_text()

    verifier = context.local_context(config.load(), tmp_path)
    result = case.check(verifier.repos()[0], verifier)
    assert result.findings == [Finding(Status.PASS, OK_MESSAGE)]


def test_15_5_3_rendering_a_linked_doc_twice_reaches_a_fixed_point() -> None:
    tests = story_docs.collect_py_tests([PY_TEST_PATH], {PY_TEST_PATH: PY_TEST}.get)
    once = story_docs.render_linked_doc(DOC, tests)
    twice = story_docs.render_linked_doc(once, tests)
    assert once == twice


def test_15_6_1_recognizes_test_calls_written_with_chained_modifiers(run_story_check: RunStoryCheck) -> None:
    test_content = (
        "it.concurrent('1.1.1 shows the widget name', async () => {});\n"
        "test.skip('1.1.2 accepts a custom color', () => {});\n"
    )
    files = {"package.json": _TS_PLAIN_PKG, DOC_PATH: _linked("1_widget.test.ts"), TS_TEST_PATH: test_content}
    result = run_story_check(story_tests_ts_check.run, files)
    assert result.findings == [Finding(Status.PASS, OK_MESSAGE)]


def test_15_7_1_scopes_each_check_to_only_its_own_language_packages_in_a_mixed_repo(
    run_story_check: RunStoryCheck,
) -> None:
    files = {
        "package.json": _TS_BUN_WORKSPACE_APPS,
        "pyproject.toml": _PY_UV_WORKSPACE_SERVICES,
        "apps/widget/package.json": _TS_BIN_PKG,
        "apps/widget/tests/stories/1_widget.md": _linked("1_widget.test.ts"),
        "apps/widget/tests/stories/1_widget.test.ts": TS_TEST,
        "services/gizmo/pyproject.toml": _PY_SCRIPTS_PYPROJECT,
    }
    ts_result = run_story_check(story_tests_ts_check.run, files)
    py_result = run_story_check(story_tests_py_check.run, files)
    assert ts_result.findings == [Finding(Status.PASS, OK_MESSAGE)]
    assert py_result.findings == [Finding(Status.FAIL, _needs_story_tests_message("services/gizmo"))]
