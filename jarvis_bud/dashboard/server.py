"""Flask dashboard for local-only configuration and status."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List

from flask import Flask, jsonify, redirect, render_template, request, send_from_directory, url_for
from werkzeug.serving import make_server

if TYPE_CHECKING:
    from jarvis_bud.main import JarvisBud


class DashboardServer:
    """Run a local-only Flask dashboard on port 8080."""

    def __init__(self, app: "JarvisBud", host: str = "127.0.0.1", port: int = 8080):
        self.app = app
        self.host = host
        self.port = port
        root = Path(__file__).parent
        self.reports_dir = Path("reports")
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self._flask = Flask(
            __name__,
            template_folder=str(root / "templates"),
        )
        self._server = None
        self._thread: threading.Thread | None = None
        self._register_routes()

    def _list_reports(self) -> List[str]:
        reports = []
        for report in sorted(self.reports_dir.glob("*.html"), reverse=True):
            reports.append(report.name)
        return reports

    def _register_routes(self) -> None:
        @self._flask.get("/")
        def index():
            return render_template(
                "index.html",
                status=self.app.get_status_snapshot(),
                config=self.app.config_manager.get_display_dict(),
                reports=self._list_reports(),
            )

        @self._flask.get("/api/status")
        def api_status():
            return jsonify(self.app.get_status_snapshot())

        @self._flask.post("/config")
        def update_config():
            form = request.form
            updates: Dict[str, Any] = {
                "openrouter.api_key": form.get("openrouter_api_key", "").strip(),
                "network.ssid": form.get("wifi_ssid", "").strip(),
                "network.password": form.get("wifi_password", "").strip(),
                "network.hostname": form.get("hostname", "").strip(),
                "tts.profile": form.get("tts_profile", "cyberpunk").strip() or "cyberpunk",
            }
            for key, value in updates.items():
                if value:
                    self.app.config_manager.set(key, value)
            self.app.config_manager.save()
            return redirect(url_for("index"))

        @self._flask.post("/emergency-stop")
        def emergency_stop():
            self.app.emergency_stop("dashboard-button")
            return redirect(url_for("index"))

        @self._flask.get("/reports")
        def reports():
            return render_template(
                "index.html",
                status=self.app.get_status_snapshot(),
                config=self.app.config_manager.get_display_dict(),
                reports=self._list_reports(),
            )

        @self._flask.get("/reports/<path:filename>")
        def report_file(filename: str):
            return send_from_directory(self.reports_dir.resolve(), filename, mimetype="text/html")

    def start(self) -> bool:
        if self._thread and self._thread.is_alive():
            return True
        try:
            self._server = make_server(self.host, self.port, self._flask)
            self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
            self._thread.start()
            return True
        except Exception:
            self._server = None
            self._thread = None
            return False

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server = None
