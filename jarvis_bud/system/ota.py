"""Simple OTA updater backed by git fetch/pull."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class OTAStatus:
    available: bool
    branch: str
    behind_count: int
    error: Optional[str] = None


class OTAUpdater:
    """Handle update detection and application from git remote."""

    def __init__(self, repo_path: str = ".", remote: str = "origin", branch: Optional[str] = None):
        self.repo_path = Path(repo_path)
        self.remote = remote
        self.branch = branch or self._detect_branch()

    def _run(self, cmd: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            cmd,
            cwd=str(self.repo_path),
            text=True,
            capture_output=True,
            check=False,
            timeout=25,
        )

    def _detect_branch(self) -> str:
        proc = self._run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
        branch = proc.stdout.strip()
        return branch or "main"

    def check_updates(self) -> OTAStatus:
        fetch = self._run(["git", "fetch", self.remote, self.branch])
        if fetch.returncode != 0:
            return OTAStatus(available=False, branch=self.branch, behind_count=0, error=fetch.stderr.strip() or "git fetch failed")

        proc = self._run(["git", "rev-list", "--count", f"HEAD..{self.remote}/{self.branch}"])
        if proc.returncode != 0:
            return OTAStatus(available=False, branch=self.branch, behind_count=0, error=proc.stderr.strip() or "git rev-list failed")
        try:
            behind = int(proc.stdout.strip() or "0")
        except ValueError:
            behind = 0
        return OTAStatus(available=behind > 0, branch=self.branch, behind_count=behind)

    def apply_update(self) -> tuple[bool, str]:
        pull = self._run(["git", "pull", self.remote, self.branch])
        if pull.returncode == 0:
            return True, pull.stdout.strip() or "Update applied."
        return False, pull.stderr.strip() or "git pull failed"
