from __future__ import annotations

import re

import yaml

from cerberus.context import Context
from cerberus.model import CheckResult, Repo, Scope

ID = "cerberus-step"
SUMMARY = "a CI workflow runs cerberus to self-verify org invariants"
SCOPE = Scope.CONTENT

_CERBERUS_CALL = re.compile(r"\bcerberus\b")


def _runs_cerberus(workflow: str) -> bool:
    try:
        doc = yaml.safe_load(workflow)
    except yaml.YAMLError:
        return False
    if not isinstance(doc, dict):
        return False
    jobs = doc.get("jobs")
    if not isinstance(jobs, dict):
        return False
    for job in jobs.values():
        steps = job.get("steps") if isinstance(job, dict) else None
        if not isinstance(steps, list):
            continue
        for step in steps:
            command = step.get("run") if isinstance(step, dict) else None
            if isinstance(command, str) and _CERBERUS_CALL.search(command):
                return True
    return False


def run(repo: Repo, ctx: Context) -> CheckResult:
    res = CheckResult(ID, repo.name)
    if any(_runs_cerberus(content) for content in ctx.workflows(repo).values()):
        res.ok("CI runs cerberus")
    else:
        res.fail("no CI workflow runs cerberus (add `uvx zyplux-cerberus` to ci)")
    return res
