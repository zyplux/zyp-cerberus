from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from cerberus import config, context
from cerberus.checks import cerberus_step_check
from cerberus.model import CheckResult, Repo, Status

RunCerberusStep = Callable[[dict[str, str]], CheckResult]


def _workflow(run_step: str) -> dict[str, str]:
    return {"ci.yml": f"jobs:\n  ci:\n    steps:\n      - run: {run_step}\n"}


@pytest.fixture
def repo() -> Repo:
    return Repo("demo")


@pytest.fixture
def ctx() -> context.Context:
    return context.local_context(config.load(), Path())


@pytest.fixture
def run_cerberus_step(monkeypatch: pytest.MonkeyPatch, repo: Repo, ctx: context.Context) -> RunCerberusStep:
    def _run(workflows: dict[str, str]) -> CheckResult:
        monkeypatch.setattr(ctx, "workflows", lambda *_: workflows)
        return cerberus_step_check.run(repo, ctx)

    return _run


@pytest.mark.parametrize("run_step", ["uv run cerberus", "uvx zyplux-cerberus"])
def test_7_1_1_passes_when_a_step_runs_cerberus_via_uv_run_or_the_published_uvx_package(
    run_cerberus_step: RunCerberusStep, run_step: str
) -> None:
    assert run_cerberus_step(_workflow(run_step)).status is Status.PASS


def test_7_2_1_fails_when_workflow_steps_exist_but_none_run_cerberus(run_cerberus_step: RunCerberusStep) -> None:
    assert run_cerberus_step(_workflow("bun run test")).status is Status.FAIL


def test_7_2_2_fails_when_the_repo_has_no_ci_workflows_at_all(run_cerberus_step: RunCerberusStep) -> None:
    assert run_cerberus_step({}).status is Status.FAIL


def test_7_3_1_errors_when_a_workflow_file_is_not_valid_yaml(run_cerberus_step: RunCerberusStep) -> None:
    assert run_cerberus_step({"ci.yml": "jobs: [unterminated"}).status is Status.ERROR
