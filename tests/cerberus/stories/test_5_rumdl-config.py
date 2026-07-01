from collections.abc import Callable
from pathlib import Path

import pytest
from cerberus import config, context
from cerberus.checks import rumdl_config_check
from cerberus.model import CheckResult, Finding, Repo, Status

FileReader = Callable[[Repo, str], str | None]

NON_CANONICAL = '[global]\ndisable = ["MD033", "MD013"]\n\n[MD024]\nsiblings-only = true\n'
UNPARSEABLE = "[global\ndisable = [\n"

FIXED_WITH_EXCLUDE = (
    "[global]\n"
    'exclude = ["reference_clones"]\n'
    "disable = [\n"
    '    "MD013", # line-length\n'
    '    "MD022", # blanks-around-headings\n'
    '    "MD031", # blanks-around-fences\n'
    '    "MD032", # blanks-around-lists\n'
    '    "MD033", # no-inline-html\n'
    "]\n"
    "\n"
    "# no-duplicate-heading\n"
    "[MD024]\n"
    "siblings-only = true\n"
)


@pytest.fixture
def repo() -> Repo:
    return Repo("demo")


@pytest.fixture
def ctx() -> context.Context:
    return context.local_context(config.load(), Path())


@pytest.fixture
def run_rumdl(monkeypatch: pytest.MonkeyPatch, repo: Repo, ctx: context.Context) -> Callable[[FileReader], CheckResult]:
    def run(reader: FileReader) -> CheckResult:
        monkeypatch.setattr(ctx, "file", reader)
        return rumdl_config_check.run(repo, ctx)

    return run


def test_5_1_1_passes_when_the_config_matches_canonical(
    run_rumdl: Callable[[FileReader], CheckResult],
) -> None:
    result = run_rumdl(lambda *_: rumdl_config_check.CANONICAL)
    assert result.findings == [Finding(Status.PASS, ".rumdl.toml matches the org canonical")]


def test_5_1_2_passes_when_a_repo_specific_exclude_list_is_set(
    run_rumdl: Callable[[FileReader], CheckResult],
) -> None:
    content = rumdl_config_check.CANONICAL.replace("]\n", ']\nexclude = ["reference_clones"]\n', 1)
    result = run_rumdl(lambda *_: content)
    assert result.findings == [Finding(Status.PASS, ".rumdl.toml matches the org canonical")]


def test_5_1_3_fails_when_the_rule_config_differs_from_canonical(
    run_rumdl: Callable[[FileReader], CheckResult],
) -> None:
    result = run_rumdl(lambda *_: NON_CANONICAL)
    assert result.findings == [Finding(Status.FAIL, ".rumdl.toml rule config does not match the org canonical")]


def test_5_1_4_fails_when_no_config_file_exists(
    run_rumdl: Callable[[FileReader], CheckResult],
) -> None:
    result = run_rumdl(lambda *_: None)
    assert result.findings == [Finding(Status.FAIL, "no .rumdl.toml at repo root")]


def test_5_1_5_errors_when_the_config_cannot_be_parsed(
    run_rumdl: Callable[[FileReader], CheckResult],
) -> None:
    result = run_rumdl(lambda *_: UNPARSEABLE)
    assert result.findings == [
        Finding(
            Status.ERROR,
            "could not parse .rumdl.toml: Expected ']' at the end of a table declaration (at line 1, column 8)",
        )
    ]


def test_5_2_1_creates_a_canonical_config_when_none_exists(tmp_path: Path) -> None:
    fixer = context.local_context(config.load(), tmp_path, fix=True)
    rumdl_config_check.run(fixer.repos()[0], fixer)
    assert (tmp_path / ".rumdl.toml").read_text() == rumdl_config_check.CANONICAL


@pytest.fixture
def fixed_rumdl_toml(tmp_path: Path) -> Path:
    config_path = tmp_path / ".rumdl.toml"
    config_path.write_text(
        '[global]\ndisable = ["MD033", "MD013"]\nexclude = ["reference_clones"]\n\n[MD024]\nsiblings-only = true\n'
    )
    fixer = context.local_context(config.load(), tmp_path, fix=True)
    rumdl_config_check.run(fixer.repos()[0], fixer)
    return config_path


def test_5_2_2_rewrites_a_non_canonical_config_to_canonical_form_preserving_exclude(
    fixed_rumdl_toml: Path,
) -> None:
    assert fixed_rumdl_toml.read_text(encoding="utf-8") == FIXED_WITH_EXCLUDE


def test_5_2_3_passes_when_re_checked_after_being_fixed(fixed_rumdl_toml: Path) -> None:
    verifier = context.local_context(config.load(), fixed_rumdl_toml.parent)
    result = rumdl_config_check.run(verifier.repos()[0], verifier)
    assert result.findings == [Finding(Status.PASS, ".rumdl.toml matches the org canonical")]
