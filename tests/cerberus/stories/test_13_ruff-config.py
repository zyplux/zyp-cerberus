from collections.abc import Callable
from pathlib import Path

import pytest
from cerberus import config, context
from cerberus.checks import ruff_config_check
from cerberus.model import CheckResult, Finding, Repo, Status

RunRuff = Callable[..., CheckResult]

_RUFF_CANONICAL = (
    "line-length = 120\n"
    'target-version = "py314"\n'
    "preview = true\n\n"
    "[lint]\n"
    'select = ["ALL"]\n'
    'ignore = ["COM812", "ISC001", "D", "DOC", "CPY001", "S404", "S603", "S607"]\n\n'
    "[lint.per-file-ignores]\n"
    '"**/tests/**" = ["ANN001", "INP001", "S101"]\n'
)

_PASS_FINDING = Finding(
    Status.PASS, 'ruff.toml is standalone, preview, select=["ALL"], relaxations within the sanctioned set'
)


@pytest.fixture
def repo() -> Repo:
    return Repo("demo")


@pytest.fixture
def ctx() -> context.Context:
    return context.local_context(config.load(), Path())


@pytest.fixture
def run_ruff(monkeypatch: pytest.MonkeyPatch, repo: Repo, ctx: context.Context) -> RunRuff:
    def run(*, ruff: str | None = _RUFF_CANONICAL, pyproject: str | None = "[project]\n") -> CheckResult:
        files = {"pyproject.toml": pyproject, "ruff.toml": ruff}
        monkeypatch.setattr(ctx, "file", lambda _r, p: files.get(p))
        return ruff_config_check.run(repo, ctx)

    return run


def test_13_1_1_skips_repos_with_no_pyproject_file(
    run_ruff: RunRuff,
) -> None:
    result = run_ruff(pyproject=None)

    assert result.findings == [Finding(Status.SKIP, "no pyproject.toml (not a Python repo)")]


def test_13_2_1_fails_when_the_ruff_config_file_is_missing(
    run_ruff: RunRuff,
) -> None:
    result = run_ruff(ruff=None)

    assert result.findings == [Finding(Status.FAIL, "no ruff.toml at repo root (ruff config must be standalone)")]


def test_13_2_2_fails_when_the_ruff_config_lives_in_pyproject_instead(
    run_ruff: RunRuff,
) -> None:
    result = run_ruff(pyproject="[tool.ruff]\nline-length = 120\n")

    assert result.findings == [
        Finding(Status.FAIL, "ruff config lives in pyproject.toml; move it to a standalone ruff.toml")
    ]


def test_13_2_3_errors_when_the_ruff_config_cannot_be_parsed(
    run_ruff: RunRuff,
) -> None:
    result = run_ruff(ruff="preview = [unterminated\n")

    assert result.findings == [Finding(Status.ERROR, "could not parse ruff.toml")]


def test_13_3_1_fails_when_preview_is_explicitly_off(
    run_ruff: RunRuff,
) -> None:
    result = run_ruff(ruff=_RUFF_CANONICAL.replace("preview = true", "preview = false"))

    assert result.findings == [Finding(Status.FAIL, "ruff.toml must set `preview = true` (found False)")]


def test_13_3_2_fails_when_preview_is_not_set(
    run_ruff: RunRuff,
) -> None:
    result = run_ruff(ruff=_RUFF_CANONICAL.replace("preview = true\n", ""))

    assert result.findings == [Finding(Status.FAIL, "ruff.toml must set `preview = true` (found None)")]


def test_13_4_1_fails_when_select_lists_specific_rules_instead_of_all(
    run_ruff: RunRuff,
) -> None:
    result = run_ruff(ruff=_RUFF_CANONICAL.replace('select = ["ALL"]', 'select = ["E", "F"]'))

    assert result.findings == [
        Finding(Status.FAIL, "ruff.toml must set `[lint] select = [\"ALL\"]` (found ['E', 'F'])")
    ]


def test_13_4_2_fails_when_select_is_set_at_the_top_level_instead_of_under_lint(
    run_ruff: RunRuff,
) -> None:
    result = run_ruff(ruff='preview = true\nselect = ["ALL"]\n')

    assert result.findings == [Finding(Status.FAIL, 'ruff.toml must set `[lint] select = ["ALL"]` (found None)')]


def test_13_5_1_passes_when_only_some_sanctioned_rules_are_ignored(
    run_ruff: RunRuff,
) -> None:
    result = run_ruff(ruff=_RUFF_CANONICAL.replace(', "S404", "S603", "S607"', ""))

    assert result.findings == [_PASS_FINDING]


def test_13_5_2_fails_and_names_the_rule_when_an_ignore_falls_outside_the_sanctioned_set(
    run_ruff: RunRuff,
) -> None:
    result = run_ruff(ruff=_RUFF_CANONICAL.replace('"S607"]', '"S607", "E501"]'))

    assert result.findings == [Finding(Status.FAIL, "ruff.toml ignores rules outside the sanctioned set: E501")]


def test_13_6_1_passes_when_there_are_no_per_file_ignores(
    run_ruff: RunRuff,
) -> None:
    ruff = _RUFF_CANONICAL.split("\n[lint.per-file-ignores]", maxsplit=1)[0] + "\n"

    result = run_ruff(ruff=ruff)

    assert result.findings == [_PASS_FINDING]


def test_13_6_2_passes_when_only_some_sanctioned_test_rules_are_relaxed(
    run_ruff: RunRuff,
) -> None:
    result = run_ruff(ruff=_RUFF_CANONICAL.replace('["ANN001", "INP001", "S101"]', '["S101"]'))

    assert result.findings == [_PASS_FINDING]


def test_13_6_3_passes_regardless_of_which_glob_names_the_test_files(
    run_ruff: RunRuff,
) -> None:
    result = run_ruff(ruff=_RUFF_CANONICAL.replace('"**/tests/**"', '"tests/**"'))

    assert result.findings == [_PASS_FINDING]


def test_13_6_4_fails_and_names_the_rule_when_a_test_relaxation_falls_outside_the_sanctioned_set(
    run_ruff: RunRuff,
) -> None:
    result = run_ruff(ruff=_RUFF_CANONICAL.replace('"S101"]', '"S101", "ANN401"]'))

    assert result.findings == [
        Finding(Status.FAIL, "per-file-ignores `**/tests/**` relaxes rules outside the sanctioned test set: ANN401")
    ]


def test_13_7_1_passes_when_preview_select_and_both_ignore_sets_are_fully_compliant(
    run_ruff: RunRuff,
) -> None:
    result = run_ruff()

    assert result.findings == [_PASS_FINDING]
