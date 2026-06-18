from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.table import Table
from typer.core import TyperGroup

from cerberus import __version__, checks, config, context
from cerberus.context import Context
from cerberus.model import CheckResult, Repo, Scope, Status
from cerberus.source import parse_org_ref


class LinterGroup(TyperGroup):
    """Make `cerberus [PATH]` lint (ESLint-style) while keeping `cerberus org ...`.

    A bare invocation, a path, or an option falls through to the `lint` command;
    a known subcommand (`org`, `list`, `version`, `lint`) dispatches normally.
    """

    default_command = "lint"

    def parse_args(self, ctx: Any, args: list[str]) -> list[str]:
        if not args:
            args = [self.default_command]
        elif args[0] not in self.commands and args[0] not in ("--help", "-h"):
            args = [self.default_command, *args]
        return super().parse_args(ctx, args)


app = typer.Typer(
    cls=LinterGroup,
    no_args_is_help=False,
    add_completion=False,
    help="Lint a repo against org invariants; `cerberus org <ORG>` scans a whole org.",
)
org_app = typer.Typer(
    no_args_is_help=False,
    add_completion=False,
    help="Scan every repo in a GitHub org (needs gh auth with admin scope).",
)
app.add_typer(org_app, name="org")

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
CheckOpt = Annotated[list[str] | None, typer.Option("--check", help="Limit to named check(s).")]
JsonOpt = Annotated[bool, typer.Option("--json", help="Emit JSON instead of a table.")]
OrgArg = Annotated[
    str, typer.Argument(metavar="ORG", help="GitHub org: bare name, github.com/<org>, or full URL.")
]


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


def _run_check(check: checks.Check, repo: Repo, ctx: Context) -> CheckResult:
    try:
        return check.run(repo, ctx)
    except Exception as exc:  # one check must not abort the whole run
        crashed = CheckResult(check.id, repo.name)
        crashed.error(f"check crashed: {exc}")
        return crashed


def _evaluate(
    ctx: Context, repos: list[Repo], selected: list[checks.Check]
) -> dict[str, dict[str, CheckResult]]:
    matrix: dict[str, dict[str, CheckResult]] = {}
    for repo in repos:
        matrix[repo.name] = {check.id: _run_check(check, repo, ctx) for check in selected}
    return matrix


def _failed(results: list[CheckResult]) -> bool:
    return any(result.status.rank >= Status.FAIL.rank for result in results)


def _matrix_failed(matrix: dict[str, dict[str, CheckResult]]) -> bool:
    return _failed([r for row in matrix.values() for r in row.values()])


def _result_json(result: CheckResult) -> dict[str, object]:
    return {
        "status": result.status.label,
        "findings": [{"status": f.status.label, "message": f.message} for f in result.findings],
    }


def _matrix_json(matrix: dict[str, dict[str, CheckResult]]) -> str:
    payload = {
        repo: {cid: _result_json(result) for cid, result in row.items()}
        for repo, row in matrix.items()
    }
    return json.dumps(payload, indent=2)


@app.command()
def version() -> None:
    """Print the cerberus version."""
    console.print(__version__)


@app.command(name="list")
def list_checks() -> None:
    """List every check, its scope, and what it verifies."""
    table = Table(title="cerberus checks")
    table.add_column("id", no_wrap=True)
    table.add_column("scope")
    table.add_column("verifies")
    for chk in checks.ALL:
        scope = "content" if chk.scope is Scope.CONTENT else "control-plane"
        table.add_row(chk.id, scope, chk.summary)
    console.print(table)


@app.command()
def lint(
    path: Annotated[
        Path, typer.Argument(help="Repo checkout to lint (default: current directory).")
    ] = Path("."),
    config_path: ConfigOpt = None,
    check: CheckOpt = None,
    json_out: JsonOpt = False,
    fix: Annotated[
        bool, typer.Option("--fix", help="Auto-fix problems where possible (not yet implemented).")
    ] = False,
) -> None:
    """Lint a repository checkout against org invariants.

    Control-plane checks (rulesets, secret provisioning) are skipped here — they
    live in `cerberus org` because the checkout cannot see them. Exits non-zero
    when a content check fails (errors fail, warnings do not), so it drops
    straight into CI like any linter.
    """
    if fix:
        err.print("[yellow]--fix is not yet implemented; running checks only.[/yellow]")

    ctx = context.local_context(config.load(config_path), path)
    repo = ctx.repos()[0]
    selected = _select_checks(check)

    results: list[CheckResult] = []
    for chk in selected:
        if chk.scope is Scope.CONTROL_PLANE:
            skipped = CheckResult(chk.id, repo.name)
            skipped.skip("evaluated by `cerberus org` (needs admin API)")
            results.append(skipped)
        else:
            results.append(_run_check(chk, repo, ctx))

    if json_out:
        console.print_json(
            json.dumps({chk.id: _result_json(r) for chk, r in zip(selected, results, strict=True)})
        )
    else:
        _render_lint(repo, results)

    if _failed(results):
        raise typer.Exit(code=1)


def _render_lint(repo: Repo, results: list[CheckResult]) -> None:
    console.print(f"[bold]{repo.name}[/bold]")
    problems = [(r.check, f) for r in results for f in r.problems]
    for check_id, finding in problems:
        console.print(f"  {_GLYPH[finding.status]} {check_id}: {finding.message}")

    if not problems:
        console.print("  [green]✓ all checks pass[/green]")
    else:
        fails = sum(1 for _, f in problems if f.status.rank >= Status.FAIL.rank)
        warns = sum(1 for _, f in problems if f.status is Status.WARN)
        console.print(
            f"\n[bold]✖ {len(problems)} problems ({fails} errors, {warns} warnings)[/bold]"
        )


@org_app.callback(invoke_without_command=True)
def org_main(ctx: typer.Context, org: OrgArg, config_path: ConfigOpt = None) -> None:
    """Scan every repo in ORG. With no subcommand, reports findings per repo."""
    try:
        login = parse_org_ref(org)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    ctx.obj = context.github_context(replace(config.load(config_path), org=login))
    if ctx.invoked_subcommand is None:
        _org_verify(ctx.obj, repo=None, check=None, json_out=False)


@org_app.command(name="repos")
def org_repos(ctx: typer.Context) -> None:
    """List the repos cerberus governs."""
    gh_ctx: Context = ctx.obj
    table = Table(title=f"{gh_ctx.org} — governed repos")
    table.add_column("repo")
    table.add_column("visibility")
    table.add_column("default branch")
    for repo in gh_ctx.repos():
        table.add_row(repo.name, repo.visibility, repo.default_branch)
    console.print(table)


@org_app.command(name="scorecard")
def org_scorecard(
    ctx: typer.Context,
    repo: RepoOpt = None,
    check: CheckOpt = None,
    json_out: JsonOpt = False,
) -> None:
    """Cross-repo pass/fail matrix."""
    gh_ctx: Context = ctx.obj
    repos = _select_repos(gh_ctx, repo)
    selected = _select_checks(check)
    matrix = _evaluate(gh_ctx, repos, selected)

    if json_out:
        console.print_json(_matrix_json(matrix))
    else:
        table = Table(title=f"{gh_ctx.org} — cerberus scorecard")
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

    if _matrix_failed(matrix):
        raise typer.Exit(code=1)


@org_app.command(name="verify")
def org_verify_command(
    ctx: typer.Context,
    repo: RepoOpt = None,
    check: CheckOpt = None,
    json_out: JsonOpt = False,
) -> None:
    """Run checks and report every finding."""
    _org_verify(ctx.obj, repo=repo, check=check, json_out=json_out)


def _org_verify(
    gh_ctx: Context, repo: list[str] | None, check: list[str] | None, json_out: bool
) -> None:
    repos = _select_repos(gh_ctx, repo)
    selected = _select_checks(check)
    matrix = _evaluate(gh_ctx, repos, selected)

    if json_out:
        console.print_json(_matrix_json(matrix))
        if _matrix_failed(matrix):
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

    if _matrix_failed(matrix):
        raise typer.Exit(code=1)
