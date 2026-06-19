from __future__ import annotations

import re
from collections.abc import Iterable

from cerberus import justfile
from cerberus.context import Context
from cerberus.model import CheckResult, Repo, Scope

ID = "justfile"
SUMMARY = "recipe names, aliases, check pipeline, wrapped tool calls, no trailing whitespace"
SCOPE = Scope.CONTENT

_SEGMENT_SPLIT = re.compile(r"&&|\|\||[|;]")
_RECIPE_LINE_PREFIXES = "@-"


def _trailing_ws_lines(content: str) -> list[int]:
    return [n for n, line in enumerate(content.split("\n"), start=1) if line != line.rstrip(" \t")]


def _strip_trailing_ws(content: str) -> str:
    return "\n".join(line.rstrip(" \t") for line in content.split("\n"))


def _leading_command(segment: str) -> str | None:
    tokens = segment.split()
    while tokens and "=" in tokens[0] and not tokens[0].startswith("-"):
        tokens = tokens[1:]
    if not tokens:
        return None
    return tokens[0].lstrip(_RECIPE_LINE_PREFIXES)


def _bare_tool_calls(bodies: dict[str, str], wrapped_tools: Iterable[str]) -> list[tuple[str, str]]:
    """Find recipes that invoke a managed tool directly instead of through its runner.

    A managed tool (`ruff`, `rumdl`, ...) must run via `uv run`/`bunx`, so a recipe
    line whose leading command is the tool itself relies on an ambient install and
    breaks on a fresh checkout. Wrappers like `uv run ruff` lead with `uv`, so they
    are accepted; only a denylisted tool in command position is flagged.
    """
    tools = set(wrapped_tools)
    seen: set[tuple[str, str]] = set()
    calls: list[tuple[str, str]] = []
    for recipe, body in bodies.items():
        for line in body.split("\n"):
            for segment in _SEGMENT_SPLIT.split(line):
                command = _leading_command(segment)
                if command is None or command not in tools:
                    continue
                if (recipe, command) not in seen:
                    seen.add((recipe, command))
                    calls.append((recipe, command))
    return calls


def run(repo: Repo, ctx: Context) -> CheckResult:
    res = CheckResult(ID, repo.name)
    content = ctx.file(repo, "justfile")
    if content is None:
        res.fail("no justfile at repo root")
        return res

    ws_lines = _trailing_ws_lines(content)
    if ws_lines:
        if ctx.fix:
            ctx.write_file(repo, "justfile", _strip_trailing_ws(content))
        else:
            res.fail(f"trailing whitespace on line(s) {', '.join(map(str, ws_lines))}")

    try:
        jf = justfile.parse(content)
    except justfile.JustfileError as err:
        res.error(f"could not parse justfile: {err}")
        return res

    cfg = ctx.config

    for alias, target in cfg.required_aliases.items():
        actual = jf.aliases.get(alias)
        if actual is None:
            res.fail(f"missing alias `{alias} := {target}`")
        elif actual != target:
            res.fail(f"alias `{alias}` targets `{actual}`, expected `{target}`")

    for alias, target in cfg.recommended_aliases.items():
        actual = jf.aliases.get(alias)
        if actual is None:
            res.warn(f"missing recommended alias `{alias} := {target}`")
        elif actual != target:
            res.warn(f"alias `{alias}` targets `{actual}`, expected `{target}`")

    for name in cfg.required_recipes:
        if name not in jf.recipes:
            res.fail(f"missing required recipe `{name}`")

    for name in cfg.recommended_recipes:
        if name not in jf.recipes:
            res.warn(f"missing recommended recipe `{name}`")

    if "default" in jf.recipes and cfg.default_recipe_marker not in jf.bodies.get("default", ""):
        res.fail(f"`default` recipe should run `{cfg.default_recipe_marker}`")

    if "check" in jf.recipes:
        deps = jf.recipes["check"]
        if not justfile.is_subsequence(list(cfg.check_pipeline), deps):
            res.fail(
                f"`check` dependencies {deps} must contain {list(cfg.check_pipeline)} in order"
            )

    for recipe, tool in _bare_tool_calls(jf.bodies, cfg.wrapped_tools):
        res.fail(
            f"recipe `{recipe}` runs `{tool}` directly; managed tools must run via `uv run`/`bunx`"
        )

    if not res.problems:
        res.ok("justfile conforms")
    return res
