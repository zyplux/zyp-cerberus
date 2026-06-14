from __future__ import annotations

import json
import subprocess
from typing import Any

from cerberus import proc


class GhError(RuntimeError):
    pass


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return proc.run(["gh", *args])
    except proc.ToolNotFoundError as err:
        raise GhError(str(err)) from err


def api(path: str, *, method: str | None = None, paginate: bool = False) -> Any:
    args = ["api"]
    if method:
        args += ["-X", method]
    if paginate:
        args += ["--paginate"]
    args.append(path)
    proc = _run(args)
    if proc.returncode != 0:
        raise GhError(proc.stderr.strip() or f"gh api {path} failed")
    out = proc.stdout.strip()
    return json.loads(out) if out else None


def raw_file(owner: str, repo: str, path: str) -> str | None:
    proc = _run(
        [
            "api",
            "-H",
            "Accept: application/vnd.github.raw",
            f"repos/{owner}/{repo}/contents/{path}",
        ]
    )
    if proc.returncode != 0:
        return None
    return proc.stdout


def list_repos(org: str) -> list[dict[str, Any]]:
    proc = _run(
        [
            "repo",
            "list",
            org,
            "--no-archived",
            "--source",
            "--limit",
            "300",
            "--json",
            "name,visibility,isArchived,isFork,defaultBranchRef",
        ]
    )
    if proc.returncode != 0:
        raise GhError(proc.stderr.strip() or f"gh repo list {org} failed")
    return json.loads(proc.stdout)
