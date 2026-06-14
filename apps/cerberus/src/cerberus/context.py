from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from cerberus import gh
from cerberus.config import Config
from cerberus.model import Repo


@dataclass
class Context:
    config: Config
    _cache: dict[Any, Any] = field(default_factory=dict)

    @property
    def org(self) -> str:
        return self.config.org

    def _cached(self, key: Any, producer: Callable[[], Any]) -> Any:
        if key not in self._cache:
            self._cache[key] = producer()
        return self._cache[key]

    def repos(self) -> list[Repo]:
        def produce() -> list[Repo]:
            out: list[Repo] = []
            for raw in gh.list_repos(self.org):
                if raw["name"] in self.config.exclude_repos or raw.get("isFork"):
                    continue
                branch = (raw.get("defaultBranchRef") or {}).get("name") or "main"
                out.append(
                    Repo(
                        name=raw["name"],
                        owner=self.org,
                        default_branch=branch,
                        visibility=str(raw["visibility"]).lower(),
                        archived=bool(raw.get("isArchived")),
                        is_fork=bool(raw.get("isFork")),
                    )
                )
            return sorted(out, key=lambda r: r.name)

        return self._cached("repos", produce)

    def file(self, repo: Repo, path: str) -> str | None:
        return self._cached(
            ("file", repo.name, path), lambda: gh.raw_file(repo.owner, repo.name, path)
        )

    def workflows(self, repo: Repo) -> dict[str, str]:
        def produce() -> dict[str, str]:
            try:
                entries = gh.api(f"repos/{repo.full_name}/contents/.github/workflows") or []
            except gh.GhError:
                return {}
            out: dict[str, str] = {}
            for entry in entries:
                name = entry.get("name", "")
                if entry.get("type") == "file" and name.endswith((".yml", ".yaml")):
                    content = gh.raw_file(repo.owner, repo.name, entry["path"])
                    if content is not None:
                        out[name] = content
            return out

        return self._cached(("workflows", repo.name), produce)

    def branch_rules(self, repo: Repo) -> list[dict[str, Any]]:
        def produce() -> list[dict[str, Any]]:
            try:
                return gh.api(f"repos/{repo.full_name}/rules/branches/{repo.default_branch}") or []
            except gh.GhError:
                return []

        return self._cached(("branch_rules", repo.name), produce)

    def repo_secrets(self, repo: Repo) -> set[str]:
        def produce() -> set[str]:
            try:
                data = gh.api(f"repos/{repo.full_name}/actions/secrets") or {}
            except gh.GhError:
                return set()
            return {s["name"] for s in data.get("secrets", [])}

        return self._cached(("repo_secrets", repo.name), produce)

    def _org_secrets(self) -> dict[str, str]:
        def produce() -> dict[str, str]:
            try:
                data = gh.api(f"orgs/{self.org}/actions/secrets") or {}
            except gh.GhError:
                return {}
            return {s["name"]: s.get("visibility", "all") for s in data.get("secrets", [])}

        return self._cached("org_secrets", produce)

    def _org_secret_selected_repos(self, name: str) -> set[str]:
        def produce() -> set[str]:
            try:
                data = gh.api(f"orgs/{self.org}/actions/secrets/{name}/repositories") or {}
            except gh.GhError:
                return set()
            return {r["name"] for r in data.get("repositories", [])}

        return self._cached(("org_secret_repos", name), produce)

    def secret_available(self, repo: Repo, name: str) -> bool:
        if name in self.repo_secrets(repo):
            return True
        visibility = self._org_secrets().get(name)
        if visibility is None:
            return False
        if visibility == "all":
            return True
        if visibility == "private":
            return repo.is_private
        if visibility == "selected":
            return repo.name in self._org_secret_selected_repos(name)
        return False

    def ruleset_active(self, name: str) -> bool:
        def produce() -> bool:
            try:
                rulesets = gh.api(f"orgs/{self.org}/rulesets") or []
            except gh.GhError:
                return False
            return any(r.get("name") == name and r.get("enforcement") == "active" for r in rulesets)

        return self._cached(("ruleset_active", name), produce)
