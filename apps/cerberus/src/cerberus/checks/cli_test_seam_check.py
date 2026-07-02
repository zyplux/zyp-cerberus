"""The cli test seam: a cli app is driven through argv, so its only public
programmatic surface is one root export (the argv entry the bin wraps), and
its user-story tests reach the app exclusively through the test package's
fixture aliases. Three facts enforce that together: the app's `exports` map
exposes nothing beyond the root seam, story tests import only `#` aliases and
node builtins, and the test package's `imports` aliases stay inside the
package so an alias cannot tunnel back into app internals.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

from cerberus.checks import story_docs
from cerberus.model import CheckResult, Repo, Scope

if TYPE_CHECKING:
    from cerberus.context import Context

ID = "cli-test-seam"
SUMMARY = "cli apps export only the root seam and their story tests import only fixture aliases and node builtins"
SCOPE = Scope.CONTENT

_SEAM_EXPORT_KEYS = frozenset({".", "./package.json"})
_ALLOWED_SPECIFIER_PREFIXES = ("#", "node:")
_STORY_TEST_PATH = re.compile(r"(?:^|/)stories/[^/]+\.test\.tsx?$")
_STATIC_IMPORT = re.compile(r"^(?:import|export)\b[^;]*?\bfrom\s+'([^']+)'", re.MULTILINE | re.DOTALL)
_SIDE_EFFECT_IMPORT = re.compile(r"^import\s+'([^']+)'", re.MULTILINE)

_OK_MESSAGE = "every cli app exports only the root seam; story tests import only fixture aliases and node builtins"


def _manifest(content: str | None) -> dict[str, Any]:
    if content is None:
        return {}
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _manifest_path(package: str) -> str:
    return f"{package}/package.json" if package else "package.json"


def _import_specifiers(content: str) -> list[str]:
    return [*_STATIC_IMPORT.findall(content), *_SIDE_EFFECT_IMPORT.findall(content)]


def _alias_targets(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [target for nested in value.values() for target in _alias_targets(nested)]
    return []


def _check_exports_surface(res: CheckResult, manifest_path: str, manifest: dict[str, Any]) -> None:
    exports = manifest.get("exports")
    if exports is None:
        res.fail(f"{manifest_path}: cli app must declare exports; without one every internal module is importable")
        return
    if not isinstance(exports, dict):
        return
    subpaths = {key for key in exports if key.startswith(".")}
    if not subpaths:
        return
    if "." not in subpaths:
        res.fail(f"{manifest_path}: cli app exports must include the '.' root seam")
    for key in sorted(subpaths - _SEAM_EXPORT_KEYS):
        res.fail(f"{manifest_path}: cli app exports expose more than the root seam — {key!r}")


def _check_story_imports(res: CheckResult, ctx: Context, repo: Repo, story_file: str) -> None:
    content = ctx.file(repo, story_file)
    if content is None:
        return
    for specifier in _import_specifiers(content):
        if not specifier.startswith(_ALLOWED_SPECIFIER_PREFIXES):
            res.fail(f"{story_file}: story test imports outside the fixtures seam — {specifier!r}")


def _governing_manifest(story_file: str, path_set: frozenset[str]) -> str | None:
    directory = story_file.rsplit("/", 1)[0]
    while "/" in directory:
        directory = directory.rsplit("/", 1)[0]
        candidate = f"{directory}/package.json"
        if candidate in path_set:
            return candidate
    return "package.json" if "package.json" in path_set else None


def _check_alias_escapes(res: CheckResult, ctx: Context, repo: Repo, manifest_path: str) -> None:
    imports = _manifest(ctx.file(repo, manifest_path)).get("imports")
    if not isinstance(imports, dict):
        return
    for alias, value in sorted(imports.items()):
        for target in _alias_targets(value):
            if ".." in target.split("/"):
                res.fail(f"{manifest_path}: imports alias escapes the test package — {alias!r} -> {target!r}")


def run(repo: Repo, ctx: Context) -> CheckResult:
    res = CheckResult(ID, repo.name)
    paths = ctx.paths(repo)
    packages = story_docs.TS.package_dirs(repo, ctx, paths)
    if not packages:
        res.skip("no TypeScript packages")
        return res

    cli_apps = [package for package in packages if _manifest(ctx.file(repo, _manifest_path(package))).get("bin")]
    if not cli_apps:
        res.skip("no cli apps")
        return res

    story_files = [path for path in paths if _STORY_TEST_PATH.search(path)]
    path_set = frozenset(paths)
    for package in sorted(cli_apps):
        manifest_path = _manifest_path(package)
        _check_exports_surface(res, manifest_path, _manifest(ctx.file(repo, manifest_path)))

        owned = sorted(path for path in story_files if story_docs.under_package(path, package))
        for story_file in owned:
            _check_story_imports(res, ctx, repo, story_file)

        governing = sorted({m for f in owned if (m := _governing_manifest(f, path_set)) is not None})
        for governing_manifest in governing:
            _check_alias_escapes(res, ctx, repo, governing_manifest)

    if not res.problems:
        res.ok(_OK_MESSAGE)
    return res
