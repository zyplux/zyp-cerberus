from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Protocol

import pytest
from cerberus import config, context
from cerberus.checks import release_bumps_check
from cerberus.model import CheckResult, Finding, Repo, Status
from cerberus.source import GitHistoryUnavailableError

if TYPE_CHECKING:
    from collections.abc import Sequence

MANIFEST = """
[[target]]
kind = "npm"
label = "@zyplux/widget"
tag_prefix = "widget-v"
version = { file = "packages/widget/package.json", json = "version" }
surface = ["packages/widget/src"]
"""

MALFORMED_MANIFEST = "not = valid = toml"
VERSION_FILE = "packages/widget/package.json"
LABEL = "@zyplux/widget"
DONE = "every published target's version tracks its surface"


class RunReleaseBumps(Protocol):
    def __call__(
        self,
        *,
        manifest: str | None = ...,
        version: str | None = ...,
        version_file_content: str | None = ...,
        tags: Sequence[str] | Exception = ...,
        changed: Sequence[str] | Exception = ...,
    ) -> CheckResult: ...


@pytest.fixture
def repo() -> Repo:
    return Repo("demo")


@pytest.fixture
def ctx() -> context.Context:
    return context.local_context(config.load(), Path())


@pytest.fixture
def run_release_bumps(monkeypatch: pytest.MonkeyPatch, repo: Repo, ctx: context.Context) -> RunReleaseBumps:
    def run(
        *,
        manifest: str | None = MANIFEST,
        version: str | None = "0.1.0",
        version_file_content: str | None = None,
        tags: Sequence[str] | Exception = (),
        changed: Sequence[str] | Exception = (),
    ) -> CheckResult:
        files: dict[str, str] = {}
        if manifest is not None:
            files["release-targets.toml"] = manifest
        if version_file_content is not None:
            files[VERSION_FILE] = version_file_content
        elif version is not None:
            files[VERSION_FILE] = f'{{"version": "{version}"}}'
        monkeypatch.setattr(ctx, "file", lambda _repo, path: files.get(path))

        def read_tags(*_: object) -> list[str]:
            if isinstance(tags, Exception):
                raise tags
            return list(tags)

        def read_changed(*_: object) -> list[str]:
            if isinstance(changed, Exception):
                raise changed
            return list(changed)

        monkeypatch.setattr(ctx, "tags", read_tags)
        monkeypatch.setattr(ctx, "changed_paths", read_changed)
        return release_bumps_check.run(repo, ctx)

    return run


def test_14_1_1_skips_repos_that_publish_nothing(run_release_bumps: RunReleaseBumps) -> None:
    result = run_release_bumps(manifest=None)
    assert result.findings == [Finding(Status.SKIP, "no release-targets.toml — repo publishes nothing")]


def test_14_1_2_errors_when_the_release_manifest_is_malformed(run_release_bumps: RunReleaseBumps) -> None:
    result = run_release_bumps(manifest=MALFORMED_MANIFEST)
    assert result.findings == [
        Finding(Status.ERROR, "release-targets.toml is malformed: Invalid value (at line 1, column 7)")
    ]


def test_14_2_1_fails_when_the_version_file_is_missing(run_release_bumps: RunReleaseBumps) -> None:
    result = run_release_bumps(version=None)
    assert result.findings == [Finding(Status.FAIL, f"{LABEL}: version file {VERSION_FILE} is missing")]


def test_14_2_2_fails_when_the_version_file_is_not_valid_json(run_release_bumps: RunReleaseBumps) -> None:
    result = run_release_bumps(version_file_content="not json")
    assert result.findings == [
        Finding(
            Status.FAIL,
            f"{LABEL}: {VERSION_FILE} is not valid JSON: Expecting value: line 1 column 1 (char 0)",
        )
    ]


def test_14_2_3_fails_when_no_version_is_found_in_the_version_file(run_release_bumps: RunReleaseBumps) -> None:
    result = run_release_bumps(version_file_content='{"name": "widget"}')
    assert result.findings == [Finding(Status.FAIL, f"{LABEL}: no version found in {VERSION_FILE}")]


def test_14_2_4_fails_when_the_declared_version_is_not_semver(run_release_bumps: RunReleaseBumps) -> None:
    result = run_release_bumps(version="not-a-version")
    assert result.findings == [Finding(Status.FAIL, f"{LABEL}: version 'not-a-version' is not semver")]


def test_14_3_1_treats_a_target_with_no_published_tags_as_not_yet_released(
    run_release_bumps: RunReleaseBumps,
) -> None:
    result = run_release_bumps(version="0.1.0", tags=[])
    assert result.findings == [
        Finding(Status.PASS, f"{LABEL}: not yet released"),
        Finding(Status.PASS, DONE),
    ]


def test_14_3_2_picks_the_highest_semver_tag_rather_than_the_last_one_listed(
    run_release_bumps: RunReleaseBumps,
) -> None:
    result = run_release_bumps(version="0.2.0", tags=["widget-v0.2.0", "widget-v0.10.0"], changed=[])
    assert result.findings == [
        Finding(Status.FAIL, f"{LABEL}: version 0.2.0 is below published 0.10.0 (widget-v0.10.0)")
    ]


def test_14_3_3_errors_when_the_published_tags_cannot_be_read(run_release_bumps: RunReleaseBumps) -> None:
    result = run_release_bumps(version="0.1.0", tags=GitHistoryUnavailableError("git tag failed"))
    assert result.findings == [Finding(Status.ERROR, f"{LABEL}: cannot read git tags: git tag failed")]


def test_14_4_1_passes_when_the_current_version_is_ahead_of_the_latest_published_release(
    run_release_bumps: RunReleaseBumps,
) -> None:
    result = run_release_bumps(version="0.2.0", tags=["widget-v0.1.0"], changed=[])
    assert result.findings == [
        Finding(Status.PASS, f"{LABEL}: 0.2.0 is ahead of published 0.1.0"),
        Finding(Status.PASS, DONE),
    ]


def test_14_4_2_fails_when_the_current_version_trails_the_latest_published_release(
    run_release_bumps: RunReleaseBumps,
) -> None:
    result = run_release_bumps(version="0.1.0", tags=["widget-v0.2.0"], changed=[])
    assert result.findings == [Finding(Status.FAIL, f"{LABEL}: version 0.1.0 is below published 0.2.0 (widget-v0.2.0)")]


def test_14_5_1_passes_when_the_release_surface_is_unchanged_since_the_latest_release(
    run_release_bumps: RunReleaseBumps,
) -> None:
    result = run_release_bumps(version="0.1.0", tags=["widget-v0.1.0"], changed=[])
    assert result.findings == [Finding(Status.PASS, DONE)]


def test_14_5_2_fails_and_names_the_required_bump_when_the_surface_changed_without_one(
    run_release_bumps: RunReleaseBumps,
) -> None:
    result = run_release_bumps(version="0.1.0", tags=["widget-v0.1.0"], changed=["packages/widget/src/a.ts"])
    assert result.findings == [
        Finding(
            Status.FAIL,
            f"{LABEL}: surface changed since widget-v0.1.0 but version is still 0.1.0 — bump it (e.g. 0.1.1)",
        )
    ]


def test_14_5_3_errors_when_the_surface_diff_cannot_be_computed(run_release_bumps: RunReleaseBumps) -> None:
    result = run_release_bumps(
        version="0.1.0", tags=["widget-v0.1.0"], changed=GitHistoryUnavailableError("git diff failed")
    )
    assert result.findings == [Finding(Status.ERROR, f"{LABEL}: cannot diff against widget-v0.1.0: git diff failed")]
