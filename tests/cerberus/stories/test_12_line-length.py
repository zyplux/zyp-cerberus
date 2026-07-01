from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from cerberus import config, context
from cerberus.checks import line_length_check
from cerberus.model import CheckResult, Finding, Repo, Status

RunLineLength = Callable[[dict[str, str]], CheckResult]

RUFF_120 = "line-length = 120\n"
PRETTIER_120 = "const config = {\n  printWidth: 120,\n};\n"


@pytest.fixture
def repo() -> Repo:
    return Repo("demo")


@pytest.fixture
def ctx() -> context.Context:
    return context.local_context(config.load(), Path())


@pytest.fixture
def run_line_length(monkeypatch: pytest.MonkeyPatch, repo: Repo, ctx: context.Context) -> RunLineLength:
    def run(files: dict[str, str]) -> CheckResult:
        monkeypatch.setattr(ctx, "file", lambda _repo, path: files.get(path))
        return line_length_check.run(repo, ctx)

    return run


def test_12_1_1_skips_repos_with_neither_a_ruff_nor_a_prettier_config(run_line_length: RunLineLength) -> None:
    result = run_line_length({})
    assert result.findings == [Finding(Status.SKIP, "no ruff or prettier config")]


def test_12_1_2_passes_when_only_a_ruff_config_is_present_and_correct(run_line_length: RunLineLength) -> None:
    result = run_line_length({"ruff.toml": RUFF_120})
    assert result.findings == [Finding(Status.PASS, "ruff and prettier both wrap at 120")]


def test_12_1_3_passes_when_only_a_prettier_config_is_present_and_correct(run_line_length: RunLineLength) -> None:
    result = run_line_length({"prettier.config.ts": PRETTIER_120})
    assert result.findings == [Finding(Status.PASS, "ruff and prettier both wrap at 120")]


def test_12_2_1_fails_when_ruff_sets_a_different_line_length(run_line_length: RunLineLength) -> None:
    result = run_line_length({"ruff.toml": "line-length = 100\n", "prettier.config.ts": PRETTIER_120})
    assert result.findings == [Finding(Status.FAIL, "ruff.toml sets line-length = 100, expected 120")]


def test_12_2_2_fails_when_ruff_does_not_set_a_line_length(run_line_length: RunLineLength) -> None:
    result = run_line_length({"ruff.toml": "[lint]\n", "prettier.config.ts": PRETTIER_120})
    assert result.findings == [Finding(Status.FAIL, "ruff.toml does not set line-length = 120")]


def test_12_3_1_fails_when_prettier_sets_a_different_line_length(run_line_length: RunLineLength) -> None:
    result = run_line_length({"ruff.toml": RUFF_120, "prettier.config.ts": "export default { printWidth: 80 };\n"})
    assert result.findings == [Finding(Status.FAIL, "prettier.config.ts sets printWidth = 80, expected 120")]


def test_12_3_2_fails_when_prettier_does_not_set_a_line_length(run_line_length: RunLineLength) -> None:
    result = run_line_length({"ruff.toml": RUFF_120, "prettier.config.ts": "export default {};\n"})
    assert result.findings == [Finding(Status.FAIL, "prettier.config.ts does not set printWidth = 120")]


def test_12_4_1_passes_when_ruff_and_prettier_both_match_the_standard(run_line_length: RunLineLength) -> None:
    result = run_line_length({"ruff.toml": RUFF_120, "prettier.config.ts": PRETTIER_120})
    assert result.findings == [Finding(Status.PASS, "ruff and prettier both wrap at 120")]
