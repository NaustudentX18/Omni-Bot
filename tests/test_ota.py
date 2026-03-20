"""OTA updater tests."""

from __future__ import annotations

from types import SimpleNamespace

from jarvis_bud.system.ota import OTAUpdater


def test_check_updates_reports_pending_commits():
    updater = OTAUpdater(repo_path=".")
    calls = []

    def fake_run(cmd):
        calls.append(cmd)
        if cmd[:2] == ["git", "fetch"]:
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        if cmd[:3] == ["git", "rev-list", "--count"]:
            return SimpleNamespace(returncode=0, stdout="3\n", stderr="")
        if cmd[:3] == ["git", "rev-parse", "--abbrev-ref"]:
            return SimpleNamespace(returncode=0, stdout="main\n", stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    updater._run = fake_run  # type: ignore[method-assign]
    updater.branch = "main"
    status = updater.check_updates()
    assert status.available is True
    assert status.behind_count == 3
    assert calls[0][:2] == ["git", "fetch"]


def test_apply_update_returns_failure_message():
    updater = OTAUpdater(repo_path=".")
    updater._run = lambda _cmd: SimpleNamespace(returncode=1, stdout="", stderr="pull failed")  # type: ignore[method-assign]
    ok, message = updater.apply_update()
    assert ok is False
    assert "pull failed" in message
