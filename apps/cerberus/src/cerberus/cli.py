from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from cerberus import __version__, checks, config
from cerberus.context import Context
from cerberus.model import CheckResult, Repo, Status

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="Verify zyplux org invariants across repos.",
)
console = Console()
err = Console(stderr=True)

_GLYPH = {
    Status.PASS: "[green]✓[/green]",
    Status.SKIP: "[dim]○[/dim]",
    Status.WARN: "[yellow]●[/yellow]",
    Status.FAIL: "[red]✗[/red]",
    Status.ERROR: "[magenta]‼[/magenta]",
}

ConfigOpt = Annotated[Path | None, typer.Option("--config", help="Path to a cerberus.toml.")]
RepoOpt = Annotated[list[str] | None, typer.Option("--repo", "-r", help="Limit to repo(s).")]
CheckOpt = Annotated[list[str] | None, typer.Option("--check", "-k", help="Limit to check(s).")]
JsonOpt = Annotated[bool, typer.Option("--json", help="Emit JSON instead of a table.")]
StrictOpt = Annotated[bool, typer.Option("--strict", help="Treat warnings as failures.")]


def _context(config_path: Path | None) -> Context:
    return Context(config=config.load(config_path))


def _select_repos(ctx: Context, only: list[str] | None) -> list[Repo]:
    repos = ctx.repos()
    if only:
        wanted = set(only)
        repos = [r for r in repos if r.name in wanted]
        missing = wanted - {r.name for r in repos}
        if missing:
            err.print(f"[yellow]unknown repos ignored: {', '.join(sorted(missing))}[/yellow]")
    return repos


def _select_checks(only: list[str] | None) -> list[checks.Check]:
    if not only:
        return list(checks.ALL)
    selected = []
    for cid in only:
        if cid not in checks.BY_ID:
            raise typer.BadParameter(f"unknown check `{cid}` (known: {', '.join(checks.BY_ID)})")
        selected.append(checks.BY_ID[cid])
    return selected


def _evaluate(
    ctx: Context, repos: list[Repo], selected: list[checks.Check]
) -> dict[str, dict[str, CheckResult]]:
    matrix: dict[str, dict[str, CheckResult]] = {}
    for repo in repos:
        row: dict[str, CheckResult] = {}
        for check in selected:
            try:
                row[check.id] = check.run(repo, ctx)
            except Exception as exc:  # one check must not abort the whole run
                crashed = CheckResult(check.id, repo.name)
                crashed.error(f"check crashed: {exc}")
                row[check.id] = crashed
        matrix[repo.name] = row
    return matrix


def _failed(matrix: dict[str, dict[str, CheckResult]], strict: bool) -> bool:
    floor = Status.WARN if strict else Status.FAIL
    return any(
        result.status.rank >= floor.rank for row in matrix.values() for result in row.values()
    )


def _as_json(matrix: dict[str, dict[str, CheckResult]]) -> str:
    payload = {
        repo: {
            cid: {
                "status": result.status.label,
                "findings": [
                    {"status": f.status.label, "message": f.message} for f in result.findings
                ],
            }
            for cid, result in row.items()
        }
        for repo, row in matrix.items()
    }
    return json.dumps(payload, indent=2)


@app.command()
def version() -> None:
    """Print the cerberus version."""
    console.print(__version__)


@app.command(name="repos")
def list_repos(config_path: ConfigOpt = None) -> None:
    """List the org repos cerberus governs."""
    ctx = _context(config_path)
    table = Table(title=f"{ctx.org} — governed repos")
    table.add_column("repo")
    table.add_column("visibility")
    table.add_column("default branch")
    for repo in ctx.repos():
        table.add_row(repo.name, repo.visibility, repo.default_branch)
    console.print(table)


@app.command()
def scorecard(
    config_path: ConfigOpt = None,
    repo: RepoOpt = None,
    check: CheckOpt = None,
    json_out: JsonOpt = False,
    strict: StrictOpt = False,
) -> None:
    """Cross-repo pass/fail matrix."""
    ctx = _context(config_path)
    repos = _select_repos(ctx, repo)
    selected = _select_checks(check)
    matrix = _evaluate(ctx, repos, selected)

    if json_out:
        console.print_json(_as_json(matrix))
    else:
        table = Table(title=f"{ctx.org} — cerberus scorecard")
        table.add_column("repo", no_wrap=True)
        for chk in selected:
            table.add_column(chk.id, justify="center")
        for repo_obj in repos:
            row = matrix[repo_obj.name]
            cells = [_GLYPH[row[chk.id].status] for chk in selected]
            table.add_row(repo_obj.name, *cells)
        console.print(table)
        console.print(
            "legend  "
            "[green]✓[/green] pass  [yellow]●[/yellow] warn  "
            "[red]✗[/red] fail  [magenta]‼[/magenta] error  [dim]○[/dim] skip"
        )

    if _failed(matrix, strict):
        raise typer.Exit(code=1)


@app.command()
def verify(
    config_path: ConfigOpt = None,
    repo: RepoOpt = None,
    check: CheckOpt = None,
    json_out: JsonOpt = False,
    strict: StrictOpt = False,
) -> None:
    """Run checks and report every finding."""
    ctx = _context(config_path)
    repos = _select_repos(ctx, repo)
    selected = _select_checks(check)
    matrix = _evaluate(ctx, repos, selected)

    if json_out:
        console.print_json(_as_json(matrix))
        if _failed(matrix, strict):
            raise typer.Exit(code=1)
        return

    for repo_obj in repos:
        row = matrix[repo_obj.name]
        console.print(f"\n[bold]{repo_obj.name}[/bold]")
        for chk in selected:
            result = row[chk.id]
            shown = result.problems or [f for f in result.findings if f.status is Status.SKIP]
            if not shown:
                console.print(f"  {_GLYPH[Status.PASS]} {chk.id}")
                continue
            console.print(f"  {_GLYPH[result.status]} {chk.id}")
            for finding in shown:
                console.print(f"      {_GLYPH[finding.status]} {finding.message}")

    if _failed(matrix, strict):
        raise typer.Exit(code=1)
