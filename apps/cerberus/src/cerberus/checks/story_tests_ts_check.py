from __future__ import annotations

from typing import TYPE_CHECKING

from cerberus.checks import story_docs
from cerberus.model import CheckResult, Repo, Scope

if TYPE_CHECKING:
    from cerberus.context import Context

ID = "story-tests-ts"
SUMMARY = "every ### criterion header in tests/**/stories/*.md has a matching, title-matched vitest test"
SCOPE = Scope.CONTENT


def run(repo: Repo, ctx: Context) -> CheckResult:
    res = CheckResult(ID, repo.name)
    if story_docs.has_uv_workspace(repo, ctx) and not story_docs.has_bun_workspace(repo, ctx):
        res.skip("uv workspace monorepo present, no bun workspace; not applicable")
        return res

    story_docs.run_story_check(repo, ctx, res, story_docs.TS)
    return res
