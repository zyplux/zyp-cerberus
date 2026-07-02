from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from cerberus import config, context
from cerberus.checks import ci_workflow_check
from cerberus.model import CheckResult, Finding, Repo, Status

RunCiWorkflow = Callable[[str | None], CheckResult]


@pytest.fixture
def repo() -> Repo:
    return Repo("demo")


@pytest.fixture
def ctx() -> context.Context:
    return context.local_context(config.load(), Path())


@pytest.fixture
def run_ci_workflow(monkeypatch: pytest.MonkeyPatch, repo: Repo, ctx: context.Context) -> RunCiWorkflow:
    def _run(workflow_content: str | None) -> CheckResult:
        reader = (
            (lambda _repo, _path: None)
            if workflow_content is None
            else (lambda _repo, path: workflow_content if path.endswith((".yml", ".yaml")) else None)
        )
        monkeypatch.setattr(ctx, "file", reader)
        return ci_workflow_check.run(repo, ctx)

    return _run


def test_3_1_1_fails_when_no_workflow_file_exists(run_ci_workflow: RunCiWorkflow) -> None:
    result = run_ci_workflow(None)
    assert result.findings == [Finding(Status.FAIL, "no .github/workflows/ci.yml")]


def test_3_1_2_errors_on_invalid_yaml(run_ci_workflow: RunCiWorkflow) -> None:
    result = run_ci_workflow("a: [unterminated")
    assert result.status is Status.ERROR
    assert result.findings[0].message.startswith("ci.yml is not valid YAML: ")


def test_3_1_3_errors_when_the_workflow_is_not_a_mapping(run_ci_workflow: RunCiWorkflow) -> None:
    result = run_ci_workflow("- just\n- a\n- list\n")
    assert result.findings == [Finding(Status.ERROR, "ci.yml did not parse to a mapping")]


def test_3_1_4_passes_when_the_workflow_lives_at_the_yaml_extension(
    monkeypatch: pytest.MonkeyPatch, repo: Repo, ctx: context.Context
) -> None:
    workflow = "on: pull_request\njobs:\n  ci:\n    name: ci\n"
    monkeypatch.setattr(ctx, "file", lambda _repo, path: workflow if path == ".github/workflows/ci.yaml" else None)
    result = ci_workflow_check.run(repo, ctx)
    assert result.findings == [Finding(Status.PASS, "ci workflow present and wired")]


def test_3_2_1_fails_without_a_job_named_ci(run_ci_workflow: RunCiWorkflow) -> None:
    result = run_ci_workflow("on: [pull_request, push]\njobs:\n  build:\n    name: build\n")
    assert result.findings == [Finding(Status.FAIL, "no job named `ci` (the required status-check context)")]


def test_3_2_2_passes_when_a_job_id_is_named_ci(run_ci_workflow: RunCiWorkflow) -> None:
    result = run_ci_workflow("on: [pull_request, push]\njobs:\n  ci:\n    runs-on: x\n")
    assert result.findings == [Finding(Status.PASS, "ci workflow present and wired")]


def test_3_2_3_passes_when_a_job_name_field_is_ci(run_ci_workflow: RunCiWorkflow) -> None:
    result = run_ci_workflow("on: pull_request\njobs:\n  build:\n    name: ci\n")
    assert result.findings == [Finding(Status.PASS, "ci workflow present and wired")]


def test_3_3_1_fails_without_a_pull_request_trigger(run_ci_workflow: RunCiWorkflow) -> None:
    result = run_ci_workflow("on: push\njobs:\n  ci:\n    name: ci\n")
    assert result.findings == [Finding(Status.FAIL, "ci.yml does not trigger on pull_request")]


@pytest.mark.parametrize("trigger", ["pull_request", "pull_request_target"])
def test_3_3_2_passes_with_a_pull_request_or_pull_request_target_trigger(
    run_ci_workflow: RunCiWorkflow, trigger: str
) -> None:
    result = run_ci_workflow(f"on: {trigger}\njobs:\n  ci:\n    name: ci\n")
    assert result.findings == [Finding(Status.PASS, "ci workflow present and wired")]


def test_3_3_3_passes_when_the_on_key_parses_to_a_boolean(run_ci_workflow: RunCiWorkflow) -> None:
    bare_on_key_parsed_as_pyyaml_bool = "on:\n  pull_request:\n  push:\njobs:\n  ci:\n    name: ci\n"
    result = run_ci_workflow(bare_on_key_parsed_as_pyyaml_bool)
    assert result.findings == [Finding(Status.PASS, "ci workflow present and wired")]
