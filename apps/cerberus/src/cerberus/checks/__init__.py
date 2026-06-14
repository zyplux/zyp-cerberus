from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from cerberus.checks import (
    ci_workflow_check,
    codeowners_check,
    justfile_check,
    ruleset_check,
    secrets_check,
)
from cerberus.context import Context
from cerberus.model import CheckResult, Repo


@dataclass(frozen=True)
class Check:
    id: str
    summary: str
    run: Callable[[Repo, Context], CheckResult]


ALL: tuple[Check, ...] = tuple(
    Check(module.ID, module.SUMMARY, module.run)
    for module in (
        justfile_check,
        ci_workflow_check,
        ruleset_check,
        secrets_check,
        codeowners_check,
    )
)

BY_ID: dict[str, Check] = {check.id: check for check in ALL}
