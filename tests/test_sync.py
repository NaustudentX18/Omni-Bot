"""Multi-device sync tests."""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from jarvis_bud.system.sync import MultiDeviceSync


def test_sync_http_status_and_target_endpoint(tmp_path: Path):
    targets: list[str] = []

    def _get_state():
        return {"targets": list(targets), "current_bud": "Fogo"}

    def _add_target(target: str):
        targets.append(target)

    sync = MultiDeviceSync(
        get_state=_get_state,
        add_target=_add_target,
        reports_dir=str(tmp_path / "reports"),
        port=18091,
    )
    assert sync.start() is True
    try:
        with urllib.request.urlopen("http://127.0.0.1:18091/status", timeout=2.0) as response:
            payload = json.loads(response.read().decode("utf-8"))
        assert payload["current_bud"] == "Fogo"

        body = json.dumps({"target": "10.0.0.5"}).encode("utf-8")
        req = urllib.request.Request(
            "http://127.0.0.1:18091/targets",
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=2.0) as response:
            assert response.status == 200
        assert "10.0.0.5" in targets
    finally:
        sync.stop()
