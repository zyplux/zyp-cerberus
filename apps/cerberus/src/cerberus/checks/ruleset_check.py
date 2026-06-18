from __future__ import annotations

from typing import Any

from cerberus.context import Context
from cerberus.model import CheckResult, Repo, Scope

ID = "ruleset"
SUMMARY = "default branch protected by the org baseline ruleset"
SCOPE = Scope.CONTROL_PLANE


def _by_type(rules: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {rule["type"]: rule for rule in rules}


def run(repo: Repo, ctx: Context) -> CheckResult:
    res = CheckResult(ID, repo.name)
    cfg = ctx.config

    if not ctx.ruleset_active(cfg.ruleset_name):
        res.fail(f"org ruleset `{cfg.ruleset_name}` is absent or not active")

    rules = _by_type(ctx.branch_rules(repo))

    pr = rules.get("pull_request")
    if pr is None:
        res.fail("default branch does not require a pull request")
    else:
        params = pr.get("parameters", {})
        if params.get("required_approving_review_count", 0) < 1:
            res.fail("pull requests do not require an approving review")
        if not params.get("require_code_owner_review"):
            res.warn("code-owner review not required")

    checks = rules.get("required_status_checks")
    if checks is None:
        res.fail("no required status checks on default branch")
    else:
        contexts = [
            c.get("context") for c in checks.get("parameters", {}).get("required_status_checks", [])
        ]
        if "ci" not in contexts:
            res.fail(f"required status checks {contexts} do not include `ci`")

    if "required_linear_history" not in rules:
        res.warn("linear history not enforced")
    if "non_fast_forward" not in rules:
        res.warn("force-pushes not blocked")
    if "deletion" not in rules:
        res.warn("branch deletion not blocked")

    if not res.problems:
        res.ok("default branch baseline enforced")
    return res
