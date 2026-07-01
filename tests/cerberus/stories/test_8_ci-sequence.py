from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from cerberus import config, context
from cerberus.checks import ci_sequence_check
from cerberus.model import CheckResult, Repo, Status

RunCiSequence = Callable[..., CheckResult]

_PY_CI = (
    "jobs:\n  ci:\n    steps:\n"
    "      - run: uv sync --locked --all-groups\n"
    "      - run: uv run --no-sync vulture\n"
    "      - run: uv run --no-sync rumdl check\n"
    "      - run: uv run --no-sync ruff check\n"
    "      - run: uv run --no-sync ruff format --check\n"
    "      - run: uv run --no-sync pyrefly check\n"
    "      - run: uv run --no-sync pytest\n"
)
_TS_CI = (
    "jobs:\n  ci:\n    container: ghcr.io/zyplux/ci:1.3.14\n    steps:\n"
    "      - run: bun install --frozen-lockfile\n"
    "      - run: bun run knip\n"
    "      - run: bun run typecheck\n"
    "      - run: bun run lint\n"
    "      - run: bunx prettier --check .\n"
    "      - run: bun run test\n"
)


@pytest.fixture
def repo() -> Repo:
    return Repo("demo")


@pytest.fixture
def ctx() -> context.Context:
    return context.local_context(config.load(), Path())


@pytest.fixture
def run_ci_sequence(monkeypatch: pytest.MonkeyPatch, repo: Repo, ctx: context.Context) -> RunCiSequence:
    def _run(*, python: bool = False, ts: bool = False, ci: str = "") -> CheckResult:
        def lookup(_repo: Repo, path: str) -> str | None:
            if path == "pyproject.toml":
                return "x" if python else None
            if path == "package.json":
                return "{}" if ts else None
            if path.endswith((".yml", ".yaml")):
                return ci or None
            return None

        monkeypatch.setattr(ctx, "file", lookup)
        return ci_sequence_check.run(repo, ctx)

    return _run


def test_8_1_1_skips_repos_with_no_package_json_or_pyproject_manifest(run_ci_sequence: RunCiSequence) -> None:
    assert run_ci_sequence(ci=_PY_CI).status is Status.SKIP


def test_8_2_1_fails_when_no_ci_workflow_file_exists(run_ci_sequence: RunCiSequence) -> None:
    assert run_ci_sequence(python=True, ci="").status is Status.FAIL


def test_8_2_2_errors_when_the_ci_workflow_file_is_not_valid_yaml(run_ci_sequence: RunCiSequence) -> None:
    assert run_ci_sequence(python=True, ci="jobs: [unterminated").status is Status.ERROR


def test_8_3_1_passes_a_python_ci_workflow_that_runs_every_required_step_in_order(
    run_ci_sequence: RunCiSequence,
) -> None:
    assert run_ci_sequence(python=True, ci=_PY_CI).status is Status.PASS


@pytest.mark.parametrize(
    "ci",
    [
        _PY_CI.replace("      - run: uv run --no-sync pytest\n", ""),
        _PY_CI.replace("uv sync --locked --all-groups", "uv sync --all-groups"),
    ],
    ids=["step_missing", "step_command_wrong"],
)
def test_8_3_2_fails_when_a_required_python_step_is_missing_or_does_not_match_its_required_command(
    run_ci_sequence: RunCiSequence, ci: str
) -> None:
    assert run_ci_sequence(python=True, ci=ci).status is Status.FAIL


def test_8_3_3_fails_when_the_required_python_steps_run_out_of_canonical_order(
    run_ci_sequence: RunCiSequence,
) -> None:
    ci = (
        "jobs:\n  ci:\n    steps:\n"
        "      - run: uv sync --locked --all-groups\n"
        "      - run: uv run --no-sync pyrefly check\n"
        "      - run: uv run --no-sync vulture\n"
        "      - run: uv run --no-sync rumdl check\n"
        "      - run: uv run --no-sync ruff check\n"
        "      - run: uv run --no-sync ruff format --check\n"
        "      - run: uv run --no-sync pytest\n"
    )
    assert run_ci_sequence(python=True, ci=ci).status is Status.FAIL


def test_8_4_1_passes_a_ts_ci_workflow_that_runs_every_required_step_in_order_within_the_org_container(
    run_ci_sequence: RunCiSequence,
) -> None:
    assert run_ci_sequence(ts=True, ci=_TS_CI).status is Status.PASS


def test_8_4_2_fails_when_a_required_ts_step_is_missing_or_does_not_match_its_required_command(
    run_ci_sequence: RunCiSequence,
) -> None:
    ci = _TS_CI.replace("      - run: bun run knip\n", "")
    assert run_ci_sequence(ts=True, ci=ci).status is Status.FAIL


def test_8_4_3_fails_when_the_required_ts_steps_run_out_of_canonical_order(run_ci_sequence: RunCiSequence) -> None:
    ci = (
        "jobs:\n  ci:\n    container: ghcr.io/zyplux/ci:1.3.14\n    steps:\n"
        "      - run: bun install --frozen-lockfile\n"
        "      - run: bun run typecheck\n"
        "      - run: bun run knip\n"
        "      - run: bun run lint\n"
        "      - run: bunx prettier --check .\n"
        "      - run: bun run test\n"
    )
    assert run_ci_sequence(ts=True, ci=ci).status is Status.FAIL


def test_8_4_4_fails_when_the_ts_job_does_not_run_in_the_org_container(run_ci_sequence: RunCiSequence) -> None:
    ci = _TS_CI.replace("    container: ghcr.io/zyplux/ci:1.3.14\n", "")
    assert run_ci_sequence(ts=True, ci=ci).status is Status.FAIL
