"""Dashboard integration tests."""

from __future__ import annotations

from pathlib import Path

from jarvis_bud.dashboard import DashboardServer
from jarvis_bud.main import JarvisBud


def test_dashboard_status_endpoint_returns_json(tmp_path: Path):
    app = JarvisBud(config_path=str(tmp_path / "config.json"))
    dashboard = DashboardServer(app=app)
    client = dashboard._flask.test_client()
    response = client.get("/api/status")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["current_bud"] == app.current_bud
    assert "connectivity_mode" in payload


def test_dashboard_emergency_stop_route_stops_runtime(tmp_path: Path):
    app = JarvisBud(config_path=str(tmp_path / "config.json"))
    dashboard = DashboardServer(app=app)
    client = dashboard._flask.test_client()
    response = client.post("/emergency-stop")
    assert response.status_code == 302
    assert app.is_running is False
