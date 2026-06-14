from __future__ import annotations

from cerberus import justfile
from cerberus.context import Context
from cerberus.model import CheckResult, Repo

ID = "justfile"
SUMMARY = "uniform recipe names, aliases, and check pipeline"


def run(repo: Repo, ctx: Context) -> CheckResult:
    res = CheckResult(ID, repo.name)
    content = ctx.file(repo, "justfile")
    if content is None:
        res.fail("no justfile at repo root")
        return res
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

    if not res.problems:
        res.ok("justfile conforms")
    return res
