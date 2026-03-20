"""Lightweight Flask dashboard for local configuration, status, and reports.

Runs on port 8080, local network only. No cloud dependency.
"""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

from flask import Flask, jsonify, render_template, request


def create_app(
    config_path: str = "config/config.json",
    runtime_path: str = "config/config.ini",
    audit_path: str = "logs/audit_chain.jsonl",
    jarvis_ref: Any = None,
) -> Flask:
    """Create and configure the Flask dashboard application."""

    template_dir = str(Path(__file__).parent / "templates")
    static_dir = str(Path(__file__).parent / "static")
    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
    app.config["SECRET_KEY"] = os.urandom(24).hex()

    app._jarvis = jarvis_ref
    app._config_path = config_path
    app._runtime_path = runtime_path
    app._audit_path = audit_path
    app._start_time = time.time()

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/status")
    def api_status():
        uptime = time.time() - app._start_time
        status: Dict[str, Any] = {
            "uptime_s": round(uptime, 1),
            "version": "0.2.0",
            "timestamp": time.time(),
        }
        if app._jarvis:
            jb = app._jarvis
            status["bud"] = jb.current_bud
            status["connectivity"] = jb.connectivity_mode
            status["god_mode"] = jb.god_mode
            status["is_running"] = jb.is_running
            status["is_listening"] = jb.is_listening
            battery = jb._refresh_battery_snapshot()
            status["battery_pct"] = battery["percentage"]
            status["battery_charging"] = battery["charging"]
            status["stt_available"] = jb.stt.is_available if hasattr(jb, "stt") else False
            status["tts_backend"] = jb.tts.backend
            status["dry_run"] = jb.tools.dry_run
        return jsonify(status)

    @app.route("/api/config", methods=["GET"])
    def api_config_get():
        try:
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    cfg = json.load(f)
                if isinstance(cfg.get("openrouter"), dict) and "api_key" in cfg["openrouter"]:
                    key = cfg["openrouter"]["api_key"]
                    cfg["openrouter"]["api_key"] = key[:8] + "..." if len(key) > 8 else "***"
                return jsonify(cfg)
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500
        return jsonify({})

    @app.route("/api/config", methods=["POST"])
    def api_config_post():
        try:
            data = request.get_json(force=True)
            os.makedirs(os.path.dirname(config_path) or ".", exist_ok=True)
            with open(config_path, "w") as f:
                json.dump(data, f, indent=2)
            if app._jarvis:
                app._jarvis.config_manager.load()
            return jsonify({"ok": True})
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    @app.route("/api/audit")
    def api_audit():
        events = []
        ledger = Path(audit_path)
        if ledger.exists():
            try:
                lines = ledger.read_text("utf-8").strip().splitlines()
                for line in lines[-100:]:
                    events.append(json.loads(line))
            except Exception:
                pass
        return jsonify(events)

    @app.route("/api/reports")
    def api_reports():
        reports_dir = Path("reports")
        files = []
        if reports_dir.exists():
            for f in sorted(reports_dir.glob("*.html"), key=lambda p: p.stat().st_mtime, reverse=True):
                files.append({"name": f.name, "size": f.stat().st_size, "mtime": f.stat().st_mtime})
        return jsonify(files)

    @app.route("/api/emergency-stop", methods=["POST"])
    def api_emergency_stop():
        if app._jarvis:
            app._jarvis.emergency_stop("web-dashboard")
            return jsonify({"ok": True, "message": "Emergency stop executed"})
        return jsonify({"ok": False, "message": "No active JarvisBud instance"}), 503

    @app.route("/api/ram")
    def api_ram():
        try:
            import resource
            usage_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            return jsonify({"peak_rss_mb": round(usage_kb / 1024, 1)})
        except Exception:
            return jsonify({"peak_rss_mb": -1})

    return app


def start_dashboard(
    host: str = "0.0.0.0",
    port: int = 8080,
    jarvis_ref: Any = None,
    config_path: str = "config/config.json",
    runtime_path: str = "config/config.ini",
    audit_path: str = "logs/audit_chain.jsonl",
) -> threading.Thread:
    """Start the dashboard in a background daemon thread."""
    app = create_app(
        config_path=config_path,
        runtime_path=runtime_path,
        audit_path=audit_path,
        jarvis_ref=jarvis_ref,
    )

    def _run():
        app.run(host=host, port=port, debug=False, use_reloader=False)

    thread = threading.Thread(target=_run, name="dashboard", daemon=True)
    thread.start()
    print(f"🌐 Dashboard running at http://{host}:{port}")
    return thread
