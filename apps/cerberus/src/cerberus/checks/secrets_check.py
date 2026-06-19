from __future__ import annotations

import re

from cerberus.context import Context
from cerberus.model import CheckResult, Repo, Scope

ID = "workflow-secrets"
SUMMARY = "every secret referenced in workflows is provisioned"
SCOPE = Scope.CONTROL_PLANE

_SECRET_REF = re.compile(r"secrets\.([A-Za-z_][A-Za-z0-9_]*)")
_ALWAYS_PRESENT = frozenset({"GITHUB_TOKEN"})


def run(repo: Repo, ctx: Context) -> CheckResult:
    res = CheckResult(ID, repo.name)
    workflows = ctx.workflows(repo)
    if not workflows:
        res.skip("no workflows")
        return res

    referenced: set[str] = set()
    for content in workflows.values():
        referenced.update(_SECRET_REF.findall(content))
    referenced -= _ALWAYS_PRESENT

    if not referenced:
        res.ok("no external secrets referenced")
        return res

    for name in sorted(referenced):
        if ctx.secret_available(repo, name):
            res.ok(f"`{name}` provisioned")
        else:
            res.fail(f"`{name}` referenced in workflows but not set at repo or org scope")
    return res
