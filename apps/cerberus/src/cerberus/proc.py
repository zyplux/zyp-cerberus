from __future__ import annotations

import shutil
import subprocess


class ToolNotFoundError(RuntimeError):
    pass


def run(argv: list[str]) -> subprocess.CompletedProcess[str]:
    """The single audited subprocess boundary for cerberus.

    `argv[0]` is resolved to an absolute path via PATH, `argv[1:]` are
    program-constructed (never user-derived), and the shell is never invoked, so
    there is no command-injection surface. This is the one place that touches
    `subprocess`; ruff's S603 (an audit-only rule, false-positive prone for
    non-literal argv) is ignored for this module alone.
    """
    executable = shutil.which(argv[0])
    if executable is None:
        raise ToolNotFoundError(f"`{argv[0]}` not found on PATH")
    return subprocess.run([executable, *argv[1:]], capture_output=True, text=True, check=False)
