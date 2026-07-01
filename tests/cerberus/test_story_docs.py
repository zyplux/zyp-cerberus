from pathlib import Path

import pytest
from cerberus import config, context
from cerberus.checks import story_docs, story_tests_py_check, story_tests_ts_check
from cerberus.model import Repo, Status

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
TS_TEST = (
    "test('1.1.1 shows the widget name', () => {});\n"
    "test('1.1.2 accepts a custom color', () => {});\n"
)

_BUN_WORKSPACE_PKG = '{"workspaces": ["packages/*"]}'
_UV_WORKSPACE_PYPROJECT = '[tool.uv.workspace]\nmembers = ["apps/*"]\n'
_PLAIN_PYPROJECT = '[project]\nname = "demo"\n'


def _linked(target: str) -> str:
    return DOC.replace("# 1. Configuring a widget\n", f"# 1. [Configuring a widget]({target})\n")


@pytest.fixture
def repo() -> Repo:
    return Repo("demo")


@pytest.fixture
def ctx() -> context.Context:
    return context.local_context(config.load(), Path())


def _wire(monkeypatch: pytest.MonkeyPatch, ctx: context.Context, files: dict[str, str]) -> None:
    monkeypatch.setattr(ctx, "paths", lambda _repo: sorted(files))
    monkeypatch.setattr(ctx, "file", lambda _repo, path: files.get(path))


def test_py_skips_without_story_docs(monkeypatch: pytest.MonkeyPatch, repo: Repo, ctx: context.Context) -> None:
    _wire(monkeypatch, ctx, {"README.md": "# demo\n"})
    assert story_tests_py_check.run(repo, ctx).status is Status.SKIP


def test_py_skips_on_bun_only_workspace(monkeypatch: pytest.MonkeyPatch, repo: Repo, ctx: context.Context) -> None:
    _wire(monkeypatch, ctx, {"package.json": _BUN_WORKSPACE_PKG, DOC_PATH: DOC})
    assert story_tests_py_check.run(repo, ctx).status is Status.SKIP


def test_py_runs_on_dual_workspace_repo(monkeypatch: pytest.MonkeyPatch, repo: Repo, ctx: context.Context) -> None:
    _wire(
        monkeypatch,
        ctx,
        {
            "package.json": _BUN_WORKSPACE_PKG,
            "pyproject.toml": _UV_WORKSPACE_PYPROJECT,
            DOC_PATH: _linked("test_1_widget.py"),
            PY_TEST_PATH: PY_TEST,
        },
    )
    assert story_tests_py_check.run(repo, ctx).status is Status.PASS


def test_py_passes_on_matching_story_tests(monkeypatch: pytest.MonkeyPatch, repo: Repo, ctx: context.Context) -> None:
    _wire(monkeypatch, ctx, {DOC_PATH: _linked("test_1_widget.py"), PY_TEST_PATH: PY_TEST})
    assert story_tests_py_check.run(repo, ctx).status is Status.PASS


def test_py_flags_orphan_header(monkeypatch: pytest.MonkeyPatch, repo: Repo, ctx: context.Context) -> None:
    test_content = "def test_1_1_1_shows_the_widget_name():\n    pass\n"
    _wire(monkeypatch, ctx, {DOC_PATH: DOC, PY_TEST_PATH: test_content})
    result = story_tests_py_check.run(repo, ctx)
    assert result.status is Status.FAIL
    assert any("1.1.2" in f.message for f in result.problems)


def test_py_flags_orphan_test(monkeypatch: pytest.MonkeyPatch, repo: Repo, ctx: context.Context) -> None:
    doc = "# 1. Configuring a widget\n\n### 1.1.1 shows the widget name\n"
    _wire(monkeypatch, ctx, {DOC_PATH: doc, PY_TEST_PATH: PY_TEST})
    result = story_tests_py_check.run(repo, ctx)
    assert result.status is Status.FAIL
    assert any("1.1.2" in f.message for f in result.problems)


def test_py_flags_title_drift(monkeypatch: pytest.MonkeyPatch, repo: Repo, ctx: context.Context) -> None:
    test_content = PY_TEST.replace("shows_the_widget_name", "shows_a_different_name")
    _wire(monkeypatch, ctx, {DOC_PATH: DOC, PY_TEST_PATH: test_content})
    result = story_tests_py_check.run(repo, ctx)
    assert result.status is Status.FAIL
    assert any("drift" in f.message for f in result.problems)


def test_py_flags_header_in_wrong_section_doc(monkeypatch: pytest.MonkeyPatch, repo: Repo, ctx: context.Context) -> None:
    stray_doc = DOC.replace("### 1.1.2", "### 2.1.2")
    _wire(monkeypatch, ctx, {DOC_PATH: stray_doc, PY_TEST_PATH: PY_TEST.replace("test_1_1_2", "test_2_1_2")})
    result = story_tests_py_check.run(repo, ctx)
    assert result.status is Status.FAIL
    assert any("wrong section" in f.message for f in result.problems)


def test_py_flags_stale_header_link(monkeypatch: pytest.MonkeyPatch, repo: Repo, ctx: context.Context) -> None:
    unlinked_doc = DOC.replace(
        "# 1. Configuring a widget\n", "# 1. [Configuring a widget](test_wrong_file.py)\n"
    )
    _wire(monkeypatch, ctx, {DOC_PATH: unlinked_doc, PY_TEST_PATH: PY_TEST})
    result = story_tests_py_check.run(repo, ctx)
    assert result.status is Status.FAIL
    assert any("stale" in f.message for f in result.problems)


def test_py_fix_rewrites_stale_header_link(tmp_path: Path) -> None:
    stories = tmp_path / "tests" / "stories"
    stories.mkdir(parents=True)
    (stories / "1_widget.md").write_text(DOC)
    (stories / "test_1_widget.py").write_text(PY_TEST)

    fixer = context.local_context(config.load(), tmp_path, fix=True)
    story_tests_py_check.run(fixer.repos()[0], fixer)

    fixed = (stories / "1_widget.md").read_text()
    assert "[Configuring a widget](test_1_widget.py)" in fixed

    verifier = context.local_context(config.load(), tmp_path)
    assert story_tests_py_check.run(verifier.repos()[0], verifier).status is Status.PASS


def test_ts_skips_without_story_docs(monkeypatch: pytest.MonkeyPatch, repo: Repo, ctx: context.Context) -> None:
    _wire(monkeypatch, ctx, {"README.md": "# demo\n"})
    assert story_tests_ts_check.run(repo, ctx).status is Status.SKIP


def test_ts_skips_on_uv_only_workspace(monkeypatch: pytest.MonkeyPatch, repo: Repo, ctx: context.Context) -> None:
    _wire(monkeypatch, ctx, {"pyproject.toml": _UV_WORKSPACE_PYPROJECT, DOC_PATH: DOC})
    assert story_tests_ts_check.run(repo, ctx).status is Status.SKIP


def test_ts_runs_on_dual_workspace_repo(monkeypatch: pytest.MonkeyPatch, repo: Repo, ctx: context.Context) -> None:
    _wire(
        monkeypatch,
        ctx,
        {
            "package.json": _BUN_WORKSPACE_PKG,
            "pyproject.toml": _UV_WORKSPACE_PYPROJECT,
            DOC_PATH: _linked("1_widget.test.ts"),
            TS_TEST_PATH: TS_TEST,
        },
    )
    assert story_tests_ts_check.run(repo, ctx).status is Status.PASS


def test_ts_passes_on_matching_story_tests(monkeypatch: pytest.MonkeyPatch, repo: Repo, ctx: context.Context) -> None:
    _wire(monkeypatch, ctx, {DOC_PATH: _linked("1_widget.test.ts"), TS_TEST_PATH: TS_TEST})
    assert story_tests_ts_check.run(repo, ctx).status is Status.PASS


def test_ts_flags_orphan_header(monkeypatch: pytest.MonkeyPatch, repo: Repo, ctx: context.Context) -> None:
    test_content = "test('1.1.1 shows the widget name', () => {});\n"
    _wire(monkeypatch, ctx, {DOC_PATH: DOC, TS_TEST_PATH: test_content})
    result = story_tests_ts_check.run(repo, ctx)
    assert result.status is Status.FAIL
    assert any("1.1.2" in f.message for f in result.problems)


def test_ts_flags_title_drift(monkeypatch: pytest.MonkeyPatch, repo: Repo, ctx: context.Context) -> None:
    test_content = TS_TEST.replace("shows the widget name", "shows a different name")
    _wire(monkeypatch, ctx, {DOC_PATH: DOC, TS_TEST_PATH: test_content})
    result = story_tests_ts_check.run(repo, ctx)
    assert result.status is Status.FAIL
    assert any("drift" in f.message for f in result.problems)


def test_ts_allows_it_and_modifiers(monkeypatch: pytest.MonkeyPatch, repo: Repo, ctx: context.Context) -> None:
    test_content = (
        "it.concurrent('1.1.1 shows the widget name', async () => {});\n"
        "test.skip('1.1.2 accepts a custom color', () => {});\n"
    )
    _wire(monkeypatch, ctx, {DOC_PATH: _linked("1_widget.test.ts"), TS_TEST_PATH: test_content})
    assert story_tests_ts_check.run(repo, ctx).status is Status.PASS


def test_ts_fix_rewrites_stale_header_link(tmp_path: Path) -> None:
    stories = tmp_path / "tests" / "stories"
    stories.mkdir(parents=True)
    (stories / "1_widget.md").write_text(DOC)
    (stories / "1_widget.test.ts").write_text(TS_TEST)

    fixer = context.local_context(config.load(), tmp_path, fix=True)
    story_tests_ts_check.run(fixer.repos()[0], fixer)

    fixed = (stories / "1_widget.md").read_text()
    assert "[Configuring a widget](1_widget.test.ts)" in fixed


def test_py_and_ts_stories_dirs_do_not_cross_own_each_other(
    monkeypatch: pytest.MonkeyPatch, repo: Repo, ctx: context.Context
) -> None:
    """A py-owned stories dir (has .py tests, no .ts tests) is invisible to the ts check, and vice versa."""
    _wire(monkeypatch, ctx, {DOC_PATH: _linked("test_1_widget.py"), PY_TEST_PATH: PY_TEST})
    assert story_tests_py_check.run(repo, ctx).status is Status.PASS
    assert story_tests_ts_check.run(repo, ctx).status is Status.SKIP


def test_render_linked_doc_is_a_fixed_point() -> None:
    tests = story_docs.collect_py_tests([PY_TEST_PATH], {PY_TEST_PATH: PY_TEST}.get)
    once = story_docs.render_linked_doc(DOC, tests)
    twice = story_docs.render_linked_doc(once, tests)
    assert once == twice
