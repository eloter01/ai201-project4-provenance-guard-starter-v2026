"""Codex Stop hook that blocks the stop until ruff and pytest pass.

Codex runs this when it is about to end a turn. If a check fails, the
hook asks Codex to keep working, with the failures as its next prompt.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# pytest exits with 5 when it collects no tests. A new repo has none yet,
# so this counts as a pass instead of blocking every early step.
PYTEST_NO_TESTS_EXIT_CODE = 5

# The reason text becomes Codex's next prompt. Capping each check's
# output keeps one noisy failure from flooding its context.
MAX_OUTPUT_CHARS = 3000

CHECK_TIMEOUT_SECONDS = 180


@dataclass(frozen=True)
class CheckResult:
    """Outcome of one check.

    Attributes:
        name: Label shown to Codex, such as "pytest".
        passed: Whether the check succeeded.
        output: Combined stdout and stderr from the command.
    """

    name: str
    passed: bool
    output: str


def read_hook_input() -> dict[str, object]:
    """Read the JSON payload Codex sends on stdin.

    Returns:
        The parsed payload, or an empty dict if stdin is empty or invalid.
    """
    # Read bytes, not text: on Windows, text mode decodes with the ANSI
    # code page, which garbles or rejects the UTF-8 that Codex sends.
    raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")
    if not raw.strip():
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def has_uncommitted_changes(repo_root: Path) -> bool:
    """Report whether the working tree differs from the last commit.

    Args:
        repo_root: Repository root directory.

    Returns:
        True if git reports changes. Also True if git can't run, so the
        checks still happen outside a git repo.
    """
    try:
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_root,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return True
    if status.returncode != 0:
        return True
    return bool(status.stdout.strip())


def find_python(repo_root: Path) -> str:
    """Pick the interpreter that has the project's dev tools.

    Args:
        repo_root: Repository root directory.

    Returns:
        The project's .venv interpreter if one exists, otherwise the
        interpreter running this hook.
    """
    candidates = (
        repo_root / ".venv" / "bin" / "python",
        repo_root / ".venv" / "Scripts" / "python.exe",
    )
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return sys.executable


def has_module(python: str, module: str) -> bool:
    """Check whether a module is installed for an interpreter.

    Args:
        python: Path to a Python interpreter.
        module: Importable module name, such as "ruff".

    Returns:
        True if the interpreter can find the module.
    """
    probe = (
        "import importlib.util, sys; "
        "sys.exit(importlib.util.find_spec(sys.argv[1]) is None)"
    )
    try:
        result = subprocess.run(
            [python, "-c", probe, module],
            capture_output=True,
            timeout=30,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def truncate(text: str, limit: int = MAX_OUTPUT_CHARS) -> str:
    """Keep the end of long output, where tools print their summaries.

    Args:
        text: Output to shorten.
        limit: Maximum number of characters to keep.

    Returns:
        The text unchanged if it fits, otherwise its last `limit`
        characters after a truncation marker.

    Raises:
        ValueError: If `limit` is not positive.
    """
    if limit <= 0:
        raise ValueError(f"limit must be positive, got {limit}")
    if len(text) <= limit:
        return text
    return "...(truncated)\n" + text[-limit:]


def run_check(
    name: str,
    command: list[str],
    repo_root: Path,
    ok_codes: tuple[int, ...] = (0,),
) -> CheckResult:
    """Run one check command and capture its result.

    Args:
        name: Label shown to Codex.
        command: Command and arguments to run.
        repo_root: Directory to run the command in.
        ok_codes: Exit codes that count as a pass.

    Returns:
        The check's outcome and trimmed output.

    Raises:
        ValueError: If `command` is empty or `repo_root` isn't a
            directory.
    """
    if not command:
        raise ValueError("command must not be empty")
    if not repo_root.is_dir():
        raise ValueError(f"not a directory: {repo_root}")
    # Python trusts a cached .pyc when the source's size and timestamp
    # look unchanged, which a quick same-size edit can fake. An empty,
    # never-written cache location forces a fresh compile every run.
    # Force UTF-8 on the pipes only, so the decoding below matches what
    # pytest writes on Windows. Full UTF-8 mode would also change how the
    # code under test opens files, making results differ from yours.
    env = {
        **os.environ,
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPYCACHEPREFIX": str(
            Path(tempfile.gettempdir()) / "codex-stop-hook-no-pyc"
        ),
        "PYTHONIOENCODING": "utf-8",
    }
    try:
        completed = subprocess.run(
            command,
            cwd=repo_root,
            env=env,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=CHECK_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        message = f"Timed out after {CHECK_TIMEOUT_SECONDS}s."
        return CheckResult(name=name, passed=False, output=message)
    output = (completed.stdout + completed.stderr).strip()
    return CheckResult(
        name=name,
        passed=completed.returncode in ok_codes,
        output=truncate(output),
    )


def run_checks(repo_root: Path, python: str) -> list[CheckResult]:
    """Run ruff lint, ruff format, and pytest.

    Args:
        repo_root: Repository root directory.
        python: Interpreter with ruff and pytest installed.

    Returns:
        One result per check, in the order they ran.
    """
    ruff = [python, "-m", "ruff"]
    return [
        run_check("ruff check", [*ruff, "check", "."], repo_root),
        run_check("ruff format", [*ruff, "format", "--check", "."], repo_root),
        run_check(
            "pytest",
            [python, "-m", "pytest", "-q"],
            repo_root,
            ok_codes=(0, PYTEST_NO_TESTS_EXIT_CODE),
        ),
    ]


def build_reason(failures: list[CheckResult]) -> str:
    """Turn failed checks into Codex's continuation prompt.

    Args:
        failures: Checks that did not pass.

    Returns:
        Instructions followed by each failing check's output.
    """
    sections = [f"## {failure.name}\n{failure.output}" for failure in failures]
    return (
        "The Stop hook found failing checks. Fix the code so they pass, "
        "without deleting or weakening tests, then report the step as "
        "usual. Don't commit.\n\n" + "\n\n".join(sections)
    )


def emit(payload: dict[str, str]) -> None:
    """Print a hook response on stdout for Codex to read.

    Args:
        payload: Response fields, such as "decision" and "reason".
    """
    print(json.dumps(payload))


def main() -> int:
    """Run the checks and tell Codex whether it may stop.

    Returns:
        The exit code. Always 0, because Codex reads the decision from
        stdout.
    """
    hook_input = read_hook_input()

    # A turn that changed nothing (a question, a plan) has nothing new to
    # verify, so skip the test run and let Codex answer right away.
    if not has_uncommitted_changes(REPO_ROOT):
        return 0

    python = find_python(REPO_ROOT)
    required = ("ruff", "pytest")
    missing = [name for name in required if not has_module(python, name)]
    if missing:
        emit(
            {
                "systemMessage": (
                    f"Stop hook skipped: {', '.join(missing)} not "
                    f"installed for {python}."
                )
            }
        )
        return 0

    results = run_checks(REPO_ROOT, python)
    failures = [result for result in results if not result.passed]
    if not failures:
        return 0

    # stop_hook_active means Codex already got one retry this turn.
    # Blocking again could loop forever, so hand control back to you.
    if hook_input.get("stop_hook_active") is True:
        names = ", ".join(failure.name for failure in failures)
        emit({"systemMessage": f"Checks still failing after a retry: {names}"})
        return 0

    emit({"decision": "block", "reason": build_reason(failures)})
    return 0


if __name__ == "__main__":
    sys.exit(main())