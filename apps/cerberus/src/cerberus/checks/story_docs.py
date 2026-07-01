"""Shared machinery for the `story-tests-py`/`story-tests-ts` checks.

Convention: any `.../stories/` directory holding numbered docs (`<n>_<slug>.md`,
`# N. Title` / `## N.M Title` / `### N.M.K Title` headers) plus same-numbered test
files in the same directory. A directory is claimed by whichever language's test
files are present there; a doc-only directory (no test files yet) is unclaimed and
evaluated by both checks until one gains tests.
"""

from __future__ import annotations

import ast
import json
import re
import tomllib
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from cerberus.context import Context
    from cerberus.model import CheckResult, Repo

PY_TEST_NAME = re.compile(r"^test_(\d+)_[^/]+\.py$")
TS_TEST_NAME = re.compile(r"^(\d+)_[^/]+\.(?:test|spec)\.tsx?$")

_STORIES_PATH_PARTS = 2  # a stories-dir path is at least "<dir>/stories/<file>"
_DOC_NAME = re.compile(r"^\d+_[^/]+\.md$")
_DOC_TITLE = re.compile(r"^# (\d+)\. (.+)$")
_STORY_HEADER = re.compile(r"^## (\d+\.\d+) (.+)$")
_CRITERION_HEADER = re.compile(r"^### (\d+(?:\.\d+)+) (.+)$")
_LINKED_TITLE = re.compile(r"^\[(?P<title>.+)\]\((?P<target>[^)]+)\)$")
_TS_TEST_CALL = re.compile(
    r"\b(?:test|it)(?:\.\w+)*\s*\(\s*(?P<quote>['\"`])(?P<id>\d+(?:\.\d+)+)\s+(?P<title>[^'\"`]*?)(?P=quote)"
)


@dataclass(frozen=True)
class StoryTest:
    story_id: str
    title: str
    file: str


@dataclass(frozen=True)
class Header:
    story_id: str
    title: str


@dataclass(frozen=True)
class Language:
    own_test_name: re.Pattern[str]
    other_test_name: re.Pattern[str]
    collect_tests: Callable[[list[str], Callable[[str], str | None]], dict[str, StoryTest]]


@dataclass(frozen=True)
class _Group:
    directory: str
    docs: dict[str, str]
    tests: dict[str, StoryTest]


def word_sequence(title: str) -> list[str]:
    """A title's comparable words — a hyphen ("non-interactive") is the same word break as a space."""
    return title.replace("-", " ").split()


def _strip_link(rest: str) -> str:
    linked = _LINKED_TITLE.match(rest)
    return linked.group("title") if linked else rest


def parse_headers(doc: str) -> dict[str, Header]:
    headers: dict[str, Header] = {}
    for line in doc.splitlines():
        header = _CRITERION_HEADER.match(line)
        if header:
            story_id, rest = header.group(1), header.group(2)
            headers[story_id] = Header(story_id, _strip_link(rest))
    return headers


def _section_files(tests: dict[str, StoryTest]) -> dict[str, str]:
    return {test.story_id.split(".")[0]: test.file for test in tests.values()}


def render_linked_doc(doc: str, tests: dict[str, StoryTest]) -> str:
    """Each doc's h1 title linked to its section's test file; h2/h3 headers always plain."""
    files = _section_files(tests)
    rendered: list[str] = []
    for raw in doc.splitlines(keepends=True):
        stripped = raw.rstrip("\n")
        newline = raw[len(stripped) :]
        doc_title = _DOC_TITLE.match(stripped)
        story = _STORY_HEADER.match(stripped)
        criterion = _CRITERION_HEADER.match(stripped)
        if doc_title:
            section, title = doc_title.group(1), _strip_link(doc_title.group(2))
            file = files.get(section)
            rendered.append(raw if file is None else f"# {section}. [{title}]({file}){newline}")
        elif story:
            story_id, title = story.group(1), _strip_link(story.group(2))
            rendered.append(f"## {story_id} {title}{newline}")
        elif criterion:
            story_id, title = criterion.group(1), _strip_link(criterion.group(2))
            rendered.append(f"### {story_id} {title}{newline}")
        else:
            rendered.append(raw)
    return "".join(rendered)


def split_id_and_title(func_name: str) -> tuple[str, str]:
    tokens = func_name.removeprefix("test_").split("_")
    cut = 0
    while cut < len(tokens) and tokens[cut].isdigit():
        cut += 1
    return ".".join(tokens[:cut]), " ".join(tokens[cut:])


def collect_py_tests(test_paths: list[str], read: Callable[[str], str | None]) -> dict[str, StoryTest]:
    tests: dict[str, StoryTest] = {}
    for path in sorted(test_paths):
        content = read(path)
        if content is None:
            continue
        try:
            tree = ast.parse(content)
        except SyntaxError:
            continue
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                story_id, title = split_id_and_title(node.name)
                if story_id:
                    tests[story_id] = StoryTest(story_id, title, path.rsplit("/", 1)[-1])
    return tests


def collect_ts_tests(test_paths: list[str], read: Callable[[str], str | None]) -> dict[str, StoryTest]:
    tests: dict[str, StoryTest] = {}
    for path in sorted(test_paths):
        content = read(path)
        if content is None:
            continue
        for match in _TS_TEST_CALL.finditer(content):
            story_id = match.group("id")
            title = match.group("title").strip()
            tests[story_id] = StoryTest(story_id, title, path.rsplit("/", 1)[-1])
    return tests


PY = Language(PY_TEST_NAME, TS_TEST_NAME, collect_py_tests)
TS = Language(TS_TEST_NAME, PY_TEST_NAME, collect_ts_tests)


def _grouped_by_stories_dir(paths: list[str], name: re.Pattern[str]) -> dict[str, list[str]]:
    dirs: dict[str, list[str]] = {}
    for path in paths:
        parts = path.split("/")
        if len(parts) < _STORIES_PATH_PARTS or parts[-2] != "stories" or "node_modules" in parts:
            continue
        if name.match(parts[-1]):
            dirs.setdefault("/".join(parts[:-1]), []).append(path)
    return dirs


def has_bun_workspace(repo: Repo, ctx: Context) -> bool:
    content = ctx.file(repo, "package.json")
    if content is None:
        return False
    try:
        manifest = json.loads(content)
    except json.JSONDecodeError:
        return False
    return isinstance(manifest, dict) and "workspaces" in manifest


def has_uv_workspace(repo: Repo, ctx: Context) -> bool:
    content = ctx.file(repo, "pyproject.toml")
    if content is None:
        return False
    try:
        config = tomllib.loads(content)
    except tomllib.TOMLDecodeError:
        return False
    tool = config.get("tool")
    uv = tool.get("uv") if isinstance(tool, dict) else None
    return isinstance(uv, dict) and "workspace" in uv


def _headers_of(group: _Group) -> dict[str, Header]:
    headers: dict[str, Header] = {}
    for content in group.docs.values():
        headers.update(parse_headers(content))
    return headers


def _check_presence(res: CheckResult, group: _Group, headers: dict[str, Header]) -> None:
    orphan_tests = sorted(set(group.tests) - set(headers))
    if orphan_tests:
        res.fail(f"{group.directory}: story test(s) with no matching ### header: {', '.join(orphan_tests)}")

    orphan_headers = sorted(set(headers) - set(group.tests))
    if orphan_headers:
        res.fail(f"{group.directory}: story-doc ### header(s) with no matching test: {', '.join(orphan_headers)}")


def _check_title_drift(res: CheckResult, group: _Group, headers: dict[str, Header]) -> None:
    for story_id in sorted(set(group.tests) & set(headers)):
        header_title, test_title = headers[story_id].title, group.tests[story_id].title
        if word_sequence(header_title) != word_sequence(test_title):
            res.fail(
                f"{group.directory}: header/test title drift for {story_id} — "
                f"header={header_title!r} test={test_title!r}"
            )


def _check_own_section(res: CheckResult, group: _Group) -> None:
    for doc_path, content in sorted(group.docs.items()):
        section = doc_path.rsplit("/", 1)[-1].split("_", 1)[0]
        strays = sorted(story_id for story_id in parse_headers(content) if story_id.split(".")[0] != section)
        if strays:
            res.fail(f"{doc_path}: story header(s) filed in the wrong section doc: {', '.join(strays)}")


def _check_header_links(res: CheckResult, ctx: Context, repo: Repo, group: _Group) -> None:
    for doc_path, content in sorted(group.docs.items()):
        relinked = render_linked_doc(content, group.tests)
        if relinked == content:
            continue
        if ctx.fix:
            ctx.write_file(repo, doc_path, relinked)
        else:
            res.fail(f"{doc_path}: story header links are stale; run with --fix")


def _check_group(res: CheckResult, ctx: Context, repo: Repo, group: _Group) -> None:
    headers = _headers_of(group)
    _check_presence(res, group, headers)
    _check_title_drift(res, group, headers)
    _check_own_section(res, group)
    _check_header_links(res, ctx, repo, group)


def _owned_directories(doc_dirs: dict[str, list[str]], own_dirs: dict[str, list[str]], other_dirs: dict[str, list[str]]) -> set[str]:
    candidates = set(doc_dirs) | set(own_dirs)
    return {directory for directory in candidates if directory in own_dirs or directory not in other_dirs}


def run_story_check(repo: Repo, ctx: Context, res: CheckResult, language: Language) -> None:
    paths = ctx.paths(repo)
    doc_dirs = _grouped_by_stories_dir(paths, _DOC_NAME)
    own_dirs = _grouped_by_stories_dir(paths, language.own_test_name)
    other_dirs = _grouped_by_stories_dir(paths, language.other_test_name)

    owned = _owned_directories(doc_dirs, own_dirs, other_dirs)
    if not owned:
        res.skip("no tests/**/stories/ docs")
        return

    def read(path: str) -> str | None:
        return ctx.file(repo, path)

    for directory in sorted(owned):
        docs = {path: content for path in doc_dirs.get(directory, []) if (content := read(path)) is not None}
        tests = language.collect_tests(own_dirs.get(directory, []), read)
        _check_group(res, ctx, repo, _Group(directory, docs, tests))

    if not res.problems:
        res.ok("every story criterion has a matching, title-matched test")
