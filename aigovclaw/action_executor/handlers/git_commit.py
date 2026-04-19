"""git-commit-and-push handler.

Always requires explicit ask-permission. The executor hard-forces
ask-permission mode regardless of authority policy overrides. If this
handler is ever invoked with an authority mode other than
ask-permission, it refuses to run.

Subprocess calls use stdlib shutil/subprocess; no third-party deps.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

from ..action_registry import ActionRequest


def handle(request: ActionRequest, dry_run: bool) -> dict[str, Any]:
    args = request.args or {}
    repo_path = args.get("repo_path")
    files = args.get("files")
    commit_message = args.get("commit_message")
    branch = args.get("branch")
    push_remote = args.get("push_remote")

    if not repo_path:
        raise ValueError("git-commit-and-push requires args['repo_path']")
    if not isinstance(files, list) or not files:
        raise ValueError("git-commit-and-push requires args['files'] as a non-empty list")
    if not commit_message:
        raise ValueError("git-commit-and-push requires args['commit_message']")

    repo = Path(str(repo_path)).expanduser().resolve()
    if not (repo / ".git").exists():
        raise FileNotFoundError(f"not a git repo: {repo}")

    if dry_run:
        return {
            "would_commit": list(files),
            "commit_message": commit_message,
            "branch": branch,
            "push_remote": push_remote,
            "repo_path": str(repo),
        }

    git = shutil.which("git")
    if not git:
        raise FileNotFoundError("git executable not on PATH")

    def run(cmd: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(
            cmd, cwd=str(repo), check=True, capture_output=True, text=True, timeout=60
        )

    if branch:
        # Checkout target branch; create if missing.
        result = subprocess.run(
            [git, "rev-parse", "--verify", branch],
            cwd=str(repo), capture_output=True, text=True,
        )
        if result.returncode == 0:
            run([git, "checkout", branch])
        else:
            run([git, "checkout", "-b", branch])

    run([git, "add", "--"] + [str(f) for f in files])

    commit = run([git, "commit", "-m", commit_message])
    sha_proc = run([git, "rev-parse", "HEAD"])
    commit_sha = sha_proc.stdout.strip()

    push_info: dict[str, Any] = {"pushed": False}
    if push_remote:
        push_cmd = [git, "push", push_remote]
        if branch:
            push_cmd.append(branch)
        push_result = run(push_cmd)
        push_info = {
            "pushed": True,
            "remote": push_remote,
            "branch": branch,
            "stdout": push_result.stdout.strip()[-500:],
        }

    return {
        "commit_sha": commit_sha,
        "files": list(files),
        "branch": branch,
        "commit_stdout": commit.stdout.strip()[-500:],
        "push": push_info,
    }
