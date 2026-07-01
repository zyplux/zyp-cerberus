import shutil
from collections.abc import Callable
from pathlib import Path

import pytest
from cerberus import config, context, justfile
from cerberus.checks import justfile_check
from cerberus.model import CheckResult, Repo, Status

requires_just = pytest.mark.skipif(shutil.which("just") is None, reason="requires the `just` binary on PATH")

RunJustfileCheck = Callable[[str | None], CheckResult]

CONFORMING = """
alias i := install
alias k := knip
alias tc := typecheck
alias l := lint
alias t := test
alias c := check
alias u := upgrade
alias ui := upgrade-interactive

default:
    @just --list
install:
    bun install
knip:
    bun run knip
typecheck:
    bun run typecheck
lint:
    bun run lint
test:
    bun run test
check: install knip typecheck lint test
upgrade:
    bun run upgrade
upgrade-interactive:
    bun run upgrade -- -i
clean:
    rm -rf node_modules
"""

MISSING_REQUIRED_ALIAS = CONFORMING.replace("alias k := knip\n", "")
WRONG_ALIAS_TARGET = CONFORMING.replace("alias k := knip\n", "alias k := lint\n")
MISSING_REQUIRED_RECIPE = CONFORMING.replace("default:\n    @just --list\n", "")
MISSING_RECOMMENDED = CONFORMING.replace("alias ui := upgrade-interactive\n", "").replace(
    "clean:\n    rm -rf node_modules\n", ""
)
WRONG_CHECK_ORDER = CONFORMING.replace(
    "check: install knip typecheck lint test", "check: install lint knip typecheck test"
)
DEFAULT_NO_LIST = CONFORMING.replace("default:\n    @just --list\n", "default:\n    echo hi\n")
BARE_TOOL_CALL = CONFORMING.replace("lint:\n    bun run lint\n", "lint:\n    rumdl check\n")
TRAILING_WHITESPACE = CONFORMING.replace(
    "check: install knip typecheck lint test\n",
    "check: install knip typecheck lint test   \n",
)

WITH_INTERPOLATION = """
recipe := "examples/recipe.toml"

default:
    @just --list

install:
    uv sync

test:
    uv run pytest

up *args:
    uv run totchef up --recipe {{ recipe }} {{ args }}

check: install test
"""


@pytest.fixture
def repo() -> Repo:
    return Repo("demo")


@pytest.fixture
def ctx() -> context.Context:
    return context.local_context(config.load(), Path())


@pytest.fixture
def run_justfile_check(monkeypatch: pytest.MonkeyPatch, repo: Repo, ctx: context.Context) -> RunJustfileCheck:
    def _run(justfile_text: str | None) -> CheckResult:
        monkeypatch.setattr(ctx, "file", lambda *_: justfile_text)
        return justfile_check.run(repo, ctx)

    return _run


@requires_just
def test_1_1_1_passes_a_fully_conforming_justfile(run_justfile_check: RunJustfileCheck) -> None:
    result = run_justfile_check(CONFORMING)
    assert (result.status, result.problems) == (Status.PASS, [])


def test_1_1_2_fails_when_the_repo_has_no_justfile_at_its_root(run_justfile_check: RunJustfileCheck) -> None:
    result = run_justfile_check(None)
    assert (result.status, [f.message for f in result.problems]) == (Status.FAIL, ["no justfile at repo root"])


@requires_just
@pytest.mark.parametrize(
    ("justfile_text", "expected_message"),
    [
        (MISSING_REQUIRED_ALIAS, "missing alias `k := knip`"),
        (WRONG_ALIAS_TARGET, "alias `k` targets `lint`, expected `knip`"),
    ],
    ids=["missing", "wrong-target"],
)
def test_1_2_1_fails_when_a_required_alias_is_missing_or_targets_the_wrong_recipe(
    run_justfile_check: RunJustfileCheck, justfile_text: str, expected_message: str
) -> None:
    result = run_justfile_check(justfile_text)
    assert (result.status, [f.message for f in result.problems]) == (Status.FAIL, [expected_message])


@requires_just
def test_1_2_2_fails_when_a_required_recipe_is_missing(run_justfile_check: RunJustfileCheck) -> None:
    result = run_justfile_check(MISSING_REQUIRED_RECIPE)
    assert (result.status, [f.message for f in result.problems]) == (
        Status.FAIL,
        ["missing required recipe `default`"],
    )


@requires_just
def test_1_2_3_fails_when_a_recommended_alias_or_recipe_is_missing(run_justfile_check: RunJustfileCheck) -> None:
    result = run_justfile_check(MISSING_RECOMMENDED)
    assert (result.status, [f.message for f in result.problems]) == (
        Status.FAIL,
        ["missing recommended alias `ui := upgrade-interactive`", "missing recommended recipe `clean`"],
    )


@requires_just
def test_1_3_1_fails_when_the_check_recipe_runs_its_steps_out_of_order(run_justfile_check: RunJustfileCheck) -> None:
    result = run_justfile_check(WRONG_CHECK_ORDER)
    assert (result.status, [f.message for f in result.problems]) == (
        Status.FAIL,
        [
            (
                "`check` dependencies ['install', 'lint', 'knip', 'typecheck', 'test'] "
                "must contain ['install', 'knip', 'typecheck', 'lint', 'test'] in order"
            )
        ],
    )


def test_1_3_2_determines_whether_one_step_list_is_an_in_order_subsequence_of_another() -> None:
    assert justfile.is_subsequence(["a", "c"], ["a", "b", "c"])
    assert justfile.is_subsequence(["install", "knip", "test"], ["install", "build", "knip", "test"])
    assert not justfile.is_subsequence(["c", "a"], ["a", "b", "c"])
    assert not justfile.is_subsequence(["x"], ["a", "b"])


@requires_just
def test_1_4_1_fails_when_the_default_recipe_does_not_list_available_commands(
    run_justfile_check: RunJustfileCheck,
) -> None:
    result = run_justfile_check(DEFAULT_NO_LIST)
    assert (result.status, [f.message for f in result.problems]) == (
        Status.FAIL,
        ["`default` recipe should run `just --list`"],
    )


@requires_just
def test_1_5_1_fails_and_names_the_tool_when_a_recipe_calls_it_directly(run_justfile_check: RunJustfileCheck) -> None:
    result = run_justfile_check(BARE_TOOL_CALL)
    assert (result.status, [f.message for f in result.problems]) == (
        Status.FAIL,
        ["recipe `lint` runs `rumdl` directly; managed tools must run via `uv run`/`bunx`"],
    )


@requires_just
def test_1_6_1_fails_when_a_recipe_line_has_trailing_whitespace(run_justfile_check: RunJustfileCheck) -> None:
    result = run_justfile_check(TRAILING_WHITESPACE)
    assert (result.status, [f.message for f in result.problems]) == (
        Status.FAIL,
        ["trailing whitespace on line(s) 23"],
    )


@requires_just
def test_1_7_1_extracts_recipes_aliases_dependencies_and_bodies_from_justfile_content() -> None:
    jf = justfile.parse(
        "alias c := check\n"
        "default:\n    @just --list\n"
        "install:\n    bun install\n"
        "check: install test\n"
        "test:\n    bun test\n"
    )
    assert (jf.aliases, jf.recipes, jf.bodies) == (
        {"c": "check"},
        {"check": ["install", "test"], "default": [], "install": [], "test": []},
        {"check": "", "default": "@just --list", "install": "bun install", "test": "bun test"},
    )


@requires_just
def test_1_7_2_collapses_interpolation_fragments_when_extracting_recipe_bodies() -> None:
    jf = justfile.parse(WITH_INTERPOLATION)
    assert jf.recipes["check"] == ["install", "test"]
    assert "uv run totchef up" in jf.bodies["up"]
