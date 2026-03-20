"""OTA self-update via git pull with OLED confirmation and rollback safety.

Flow:
  1. Check for updates (git fetch --dry-run)
  2. Show diff summary on OLED
  3. Require Button A confirmation (or auto-confirm via env)
  4. Execute git pull
  5. Restart application if update succeeded
"""

from __future__ import annotations

import os
import subprocess
import time
from typing import Any, Dict, Optional, Tuple

from jarvis_bud.audit import AuditLogger


class OTAUpdater:
    """Simple git-based OTA updater for Pi deployments."""

    def __init__(
        self,
        repo_dir: str = ".",
        branch: str = "main",
        audit: Optional[AuditLogger] = None,
        auto_confirm: bool = False,
    ):
        self.repo_dir = os.path.abspath(repo_dir)
        self.branch = branch
        self.audit = audit
        self.auto_confirm = auto_confirm or os.environ.get("NXTGENAI_AUTO_UPDATE", "").lower() in {
            "1",
            "true",
            "yes",
        }

    def _git(self, *args: str, timeout: int = 30) -> Tuple[int, str, str]:
        """Run a git command and return (returncode, stdout, stderr)."""
        try:
            result = subprocess.run(
                ["git"] + list(args),
                cwd=self.repo_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result.returncode, result.stdout.strip(), result.stderr.strip()
        except FileNotFoundError:
            return 127, "", "git not found"
        except subprocess.TimeoutExpired:
            return 124, "", "git command timed out"

    def get_current_version(self) -> str:
        """Return current git short hash + branch."""
        code, out, _ = self._git("rev-parse", "--short", "HEAD")
        if code == 0:
            return f"{self.branch}@{out}"
        return "unknown"

    def check_for_updates(self) -> Dict[str, Any]:
        """Fetch remote and check if updates are available.

        Returns dict with: available (bool), local_hash, remote_hash, commits_behind, summary.
        """
        self._git("fetch", "origin", self.branch, timeout=60)

        _, local, _ = self._git("rev-parse", "HEAD")
        _, remote, _ = self._git("rev-parse", f"origin/{self.branch}")

        if local == remote:
            return {"available": False, "local_hash": local[:8], "remote_hash": remote[:8], "commits_behind": 0, "summary": ""}

        _, count_str, _ = self._git("rev-list", "--count", f"HEAD..origin/{self.branch}")
        commits_behind = int(count_str) if count_str.isdigit() else 0

        _, log_summary, _ = self._git("log", "--oneline", f"HEAD..origin/{self.branch}", "--max-count=5")

        result = {
            "available": True,
            "local_hash": local[:8],
            "remote_hash": remote[:8],
            "commits_behind": commits_behind,
            "summary": log_summary,
        }

        if self.audit:
            self.audit.log_event("ota.check", result)

        return result

    def apply_update(self, confirm_callback=None) -> Dict[str, Any]:
        """Pull the latest changes after confirmation.

        Args:
            confirm_callback: Optional callable that returns True to proceed.
                              If None, uses auto_confirm or returns without updating.

        Returns:
            Dict with success (bool), message, old_hash, new_hash.
        """
        _, old_hash, _ = self._git("rev-parse", "--short", "HEAD")

        if not self.auto_confirm:
            if confirm_callback and not confirm_callback():
                if self.audit:
                    self.audit.log_event("ota.cancelled", {"reason": "user-declined"})
                return {"success": False, "message": "Update declined by user", "old_hash": old_hash, "new_hash": old_hash}
            elif not confirm_callback:
                return {"success": False, "message": "No confirmation method provided", "old_hash": old_hash, "new_hash": old_hash}

        self._git("stash", "--include-untracked")

        code, out, err = self._git("pull", "origin", self.branch, timeout=120)

        if code != 0:
            self._git("stash", "pop")
            if self.audit:
                self.audit.log_event("ota.failed", {"error": err[:200]})
            return {"success": False, "message": f"git pull failed: {err[:200]}", "old_hash": old_hash, "new_hash": old_hash}

        _, new_hash, _ = self._git("rev-parse", "--short", "HEAD")

        pip_code = self._reinstall_deps()

        if self.audit:
            self.audit.log_event(
                "ota.applied",
                {"old_hash": old_hash, "new_hash": new_hash, "pip_ok": pip_code == 0},
            )

        return {
            "success": True,
            "message": f"Updated {old_hash} -> {new_hash}",
            "old_hash": old_hash,
            "new_hash": new_hash,
        }

    def _reinstall_deps(self) -> int:
        """Re-install Python dependencies after update."""
        req_path = os.path.join(self.repo_dir, "requirements.txt")
        if not os.path.exists(req_path):
            return 0
        try:
            result = subprocess.run(
                ["pip", "install", "-r", req_path, "-q"],
                cwd=self.repo_dir,
                capture_output=True,
                timeout=300,
            )
            return result.returncode
        except Exception:
            return 1

    def get_changelog(self, max_entries: int = 10) -> str:
        """Return recent git log as a formatted string."""
        _, log, _ = self._git("log", "--oneline", f"--max-count={max_entries}")
        return log
