"""Flask dashboard for local-only configuration and status."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from flask import Flask, jsonify, redirect, render_template, request, send_from_directory, url_for
from werkzeug.serving import make_server

if TYPE_CHECKING:
    from jarvis_bud.main import JarvisBud

# ---------------------------------------------------------------------------
# Static data – voices, models, cloud providers
# ---------------------------------------------------------------------------

PIPER_VOICES: List[Dict[str, Any]] = [
    {
        "id": "en_US-lessac-medium",
        "name": "Lessac",
        "lang": "English (US)",
        "gender": "Female",
        "style": "Natural",
        "size_mb": 63,
        "onnx_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx",
        "json_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json",
    },
    {
        "id": "en_US-ryan-medium",
        "name": "Ryan",
        "lang": "English (US)",
        "gender": "Male",
        "style": "Natural",
        "size_mb": 63,
        "onnx_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/medium/en_US-ryan-medium.onnx",
        "json_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/medium/en_US-ryan-medium.onnx.json",
    },
    {
        "id": "en_US-amy-medium",
        "name": "Amy",
        "lang": "English (US)",
        "gender": "Female",
        "style": "Friendly",
        "size_mb": 24,
        "onnx_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx",
        "json_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx.json",
    },
    {
        "id": "en_US-joe-medium",
        "name": "Joe",
        "lang": "English (US)",
        "gender": "Male",
        "style": "Casual",
        "size_mb": 63,
        "onnx_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/joe/medium/en_US-joe-medium.onnx",
        "json_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/joe/medium/en_US-joe-medium.onnx.json",
    },
    {
        "id": "en_US-norman-medium",
        "name": "Norman",
        "lang": "English (US)",
        "gender": "Male",
        "style": "Professional",
        "size_mb": 63,
        "onnx_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/norman/medium/en_US-norman-medium.onnx",
        "json_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/norman/medium/en_US-norman-medium.onnx.json",
    },
    {
        "id": "en_US-kathleen-low",
        "name": "Kathleen",
        "lang": "English (US)",
        "gender": "Female",
        "style": "Ultralight",
        "size_mb": 5,
        "onnx_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/kathleen/low/en_US-kathleen-low.onnx",
        "json_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/kathleen/low/en_US-kathleen-low.onnx.json",
    },
    {
        "id": "en_GB-alan-medium",
        "name": "Alan",
        "lang": "English (GB)",
        "gender": "Male",
        "style": "British",
        "size_mb": 25,
        "onnx_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/alan/medium/en_GB-alan-medium.onnx",
        "json_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/alan/medium/en_GB-alan-medium.onnx.json",
    },
    {
        "id": "en_GB-jenny_dioco-medium",
        "name": "Jenny",
        "lang": "English (GB)",
        "gender": "Female",
        "style": "British",
        "size_mb": 63,
        "onnx_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/jenny_dioco/medium/en_GB-jenny_dioco-medium.onnx",
        "json_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/jenny_dioco/medium/en_GB-jenny_dioco-medium.onnx.json",
    },
]

OFFLINE_MODELS: List[Dict[str, Any]] = [
    {
        "id": "gemma-2-2b-it-Q4_K_M",
        "name": "Gemma 2 2B",
        "filename": "gemma-2-2b-it-Q4_K_M.gguf",
        "size": "1.6 GB",
        "ram": "2 GB",
        "speed": "Fast",
        "quality": "Excellent",
        "description": "Google's Gemma 2 — best balance of speed and quality on Pi Zero 2 W",
        "recommended": True,
        "url": "https://huggingface.co/bartowski/gemma-2-2b-it-GGUF/resolve/main/gemma-2-2b-it-Q4_K_M.gguf",
    },
    {
        "id": "phi-3.5-mini-instruct-Q4_K_M",
        "name": "Phi 3.5 Mini",
        "filename": "phi-3.5-mini-instruct-Q4_K_M.gguf",
        "size": "2.2 GB",
        "ram": "3 GB",
        "speed": "Medium",
        "quality": "Very Good",
        "description": "Microsoft's Phi 3.5 — strong reasoning, great at multi-step tasks",
        "recommended": False,
        "url": "https://huggingface.co/bartowski/Phi-3.5-mini-instruct-GGUF/resolve/main/Phi-3.5-mini-instruct-Q4_K_M.gguf",
    },
    {
        "id": "tinyllama-1.1b-chat-v1.0-Q4_K_M",
        "name": "TinyLlama 1.1B",
        "filename": "tinyllama-1.1b-chat-v1.0-Q4_K_M.gguf",
        "size": "670 MB",
        "ram": "1 GB",
        "speed": "Very Fast",
        "quality": "Good",
        "description": "Ultra-compact — instant responses, ideal for minimal builds",
        "recommended": False,
        "url": "https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf",
    },
]

CLOUD_PROVIDERS: List[Dict[str, Any]] = [
    {
        "id": "openrouter",
        "name": "OpenRouter",
        "icon": "🔀",
        "description": "Access 300+ models including Claude, Gemini and GPT-4. Free tier available.",
        "key_url": "https://openrouter.ai/keys",
        "key_placeholder": "sk-or-...",
        "default_model": "google/gemini-2.0-flash-lite:free",
        "models": [
            "google/gemini-2.0-flash-lite:free",
            "meta-llama/llama-3.1-8b-instruct:free",
            "anthropic/claude-3-haiku",
            "openai/gpt-4o-mini",
        ],
        "free_tier": True,
    },
    {
        "id": "anthropic",
        "name": "Anthropic",
        "icon": "⬡",
        "description": "Direct access to Claude — the world's most trusted AI assistant.",
        "key_url": "https://console.anthropic.com/keys",
        "key_placeholder": "sk-ant-...",
        "default_model": "claude-haiku-4-5-20251001",
        "models": [
            "claude-haiku-4-5-20251001",
            "claude-sonnet-4-6",
        ],
        "free_tier": False,
    },
    {
        "id": "groq",
        "name": "Groq",
        "icon": "⚡",
        "description": "Blazing-fast inference on Llama and Mixtral. Free tier with generous limits.",
        "key_url": "https://console.groq.com/keys",
        "key_placeholder": "gsk_...",
        "default_model": "llama-3.1-8b-instant",
        "models": [
            "llama-3.1-8b-instant",
            "llama3-70b-8192",
            "mixtral-8x7b-32768",
        ],
        "free_tier": True,
    },
    {
        "id": "none",
        "name": "Offline Only",
        "icon": "🔒",
        "description": "No cloud — 100% local. Your data never leaves the device.",
        "key_url": None,
        "key_placeholder": None,
        "default_model": None,
        "models": [],
        "free_tier": True,
    },
]

_VOICE_IDS = {v["id"] for v in PIPER_VOICES}


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
        # Voice download state: voice_id -> {"status": "downloading"|"done"|"error", "pct": 0-100}
        self._voice_downloads: Dict[str, Dict[str, Any]] = {}
        self._register_routes()

    def _list_reports(self) -> List[str]:
        return [r.name for r in sorted(self.reports_dir.glob("*.html"), reverse=True)]

    def _scan_local_models(self) -> List[Dict[str, Any]]:
        models_dir = Path("models")
        result = []
        for m in OFFLINE_MODELS:
            path = models_dir / m["filename"]
            entry = dict(m)
            entry["downloaded"] = path.exists()
            entry["path"] = str(path)
            result.append(entry)
        # Also pick up any unknown .gguf files
        known = {m["filename"] for m in OFFLINE_MODELS}
        if models_dir.exists():
            for f in models_dir.glob("*.gguf"):
                if f.name not in known:
                    result.append({
                        "id": f.stem,
                        "name": f.stem,
                        "filename": f.name,
                        "size": f"{f.stat().st_size / 1e9:.1f} GB",
                        "ram": "?",
                        "speed": "?",
                        "quality": "?",
                        "description": "Locally detected model",
                        "recommended": False,
                        "url": None,
                        "downloaded": True,
                        "path": str(f),
                    })
        return result

    def _scan_downloaded_voices(self) -> List[str]:
        piper_dir = Path("models/piper")
        if not piper_dir.exists():
            return []
        return [f.stem.replace(".onnx", "") for f in piper_dir.glob("*.onnx")]

    def _download_voice_bg(self, voice: Dict[str, Any]) -> None:
        vid = voice["id"]
        self._voice_downloads[vid] = {"status": "downloading", "pct": 0}
        piper_dir = Path("models/piper")
        piper_dir.mkdir(parents=True, exist_ok=True)
        try:
            aria = shutil.which("aria2c")
            for i, (url_key, fname_suffix) in enumerate([
                ("onnx_url", ".onnx"),
                ("json_url", ".onnx.json"),
            ]):
                url = voice[url_key]
                out = piper_dir / f"{vid}{fname_suffix}"
                if aria:
                    subprocess.run(
                        [aria, "-c", "-x", "4", "-s", "4", "-d", str(piper_dir),
                         "-o", out.name, url],
                        check=True, timeout=600, capture_output=True,
                    )
                else:
                    import urllib.request
                    urllib.request.urlretrieve(url, str(out))
                self._voice_downloads[vid]["pct"] = 50 * (i + 1)
            self._voice_downloads[vid] = {"status": "done", "pct": 100}
        except Exception as exc:
            self._voice_downloads[vid] = {"status": "error", "pct": 0, "error": str(exc)}

    def _register_routes(self) -> None:

        # ---- existing dashboard ------------------------------------------

        @self._flask.get("/")
        def index():
            if not self.app.config_manager.is_configured():
                return redirect(url_for("setup"))
            return render_template(
                "index.html",
                status=self.app.get_status_snapshot(),
                config=self.app.config_manager.get_display_dict(),
                reports=self._list_reports(),
                buds=self._load_buds(),
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

        @self._flask.post("/config/bud")
        def switch_bud():
            form = request.form
            bud_id     = form.get("bud_id", "").strip()
            bud_name   = form.get("bud_name", "").strip()
            bud_prompt = form.get("bud_prompt", "").strip()
            bud_color  = form.get("bud_color", "#00FF66").strip()
            if bud_id:
                self.app.config_manager.set("bud.id", bud_id)
                self.app.config_manager.set("bud.name", bud_name or bud_id)
                if bud_prompt:
                    self.app.config_manager.set("bud.system_prompt", bud_prompt)
                if bud_color:
                    self.app.config_manager.set("bud.ui_accent_color", bud_color)
                self.app.config_manager.save()
                if self.app.bud_manager:
                    try:
                        self.app.bud_manager.set_active_bud(bud_id)
                        self.app.current_bud = self.app.bud_manager.active_profile.name
                    except Exception:
                        self.app.current_bud = bud_name or bud_id
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
                buds=self._load_buds(),
            )

        @self._flask.get("/reports/<path:filename>")
        def report_file(filename: str):
            return send_from_directory(self.reports_dir.resolve(), filename, mimetype="text/html")

        # ---- setup wizard ------------------------------------------------

        @self._flask.get("/setup")
        def setup():
            return render_template(
                "setup.html",
                buds=self._load_buds(),
                voices=PIPER_VOICES,
                offline_models=OFFLINE_MODELS,
                cloud_providers=CLOUD_PROVIDERS,
                downloaded_voices=self._scan_downloaded_voices(),
            )

        @self._flask.post("/setup/save")
        def setup_save():
            try:
                data = request.get_json(force=True) or {}
                cfg = _build_config_from_wizard(data)
                os.makedirs("config", exist_ok=True)
                with open(self.app.config_manager.config_path, "w", encoding="utf-8") as fh:
                    json.dump(cfg, fh, indent=2)
                self.app.config_manager.load()
                self.app.config_manager.load_runtime()
                return jsonify({"ok": True})
            except Exception as exc:
                return jsonify({"ok": False, "error": str(exc)}), 500

        # ---- model API ---------------------------------------------------

        @self._flask.get("/api/models")
        def api_models():
            return jsonify({
                "local": self._scan_local_models(),
                "catalogue": OFFLINE_MODELS,
            })

        # ---- voice API ---------------------------------------------------

        @self._flask.get("/api/voices")
        def api_voices():
            downloaded = self._scan_downloaded_voices()
            voices_with_status = []
            for v in PIPER_VOICES:
                entry = dict(v)
                entry["downloaded"] = v["id"] in downloaded
                entry["dl_state"] = self._voice_downloads.get(v["id"], {})
                voices_with_status.append(entry)
            return jsonify({"voices": voices_with_status, "downloaded": downloaded})

        @self._flask.post("/api/voices/download")
        def api_voice_download():
            body = request.get_json(force=True) or {}
            vid = str(body.get("voice_id", "")).strip()
            if vid not in _VOICE_IDS:
                return jsonify({"ok": False, "error": "Unknown voice ID"}), 400
            if self._voice_downloads.get(vid, {}).get("status") == "downloading":
                return jsonify({"ok": True, "status": "already_downloading"})
            voice = next(v for v in PIPER_VOICES if v["id"] == vid)
            t = threading.Thread(target=self._download_voice_bg, args=(voice,), daemon=True)
            t.start()
            return jsonify({"ok": True, "status": "started"})

        @self._flask.get("/api/voices/status")
        def api_voices_status():
            return jsonify(self._voice_downloads)

    def _load_buds(self) -> List[Dict[str, Any]]:
        try:
            buds_path = Path(self.app.buds_path)
            with buds_path.open("r", encoding="utf-8") as fh:
                return json.load(fh).get("buds", [])
        except Exception:
            return []

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


def _build_config_from_wizard(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert wizard POST body into full config.json structure."""
    bud_id = str(data.get("bud_id", "fogo")).strip()
    bud_name = str(data.get("bud_name", "Fogo")).strip()
    bud_prompt = str(data.get("bud_system_prompt", "You are a helpful AI assistant.")).strip()
    bud_color = str(data.get("bud_accent_color", "#00FF66")).strip()

    offline_model_file = str(data.get("offline_model_file", "gemma-2-2b-it-Q4_K_M.gguf")).strip()
    cloud_provider = str(data.get("cloud_provider", "none")).strip()
    cloud_api_key = str(data.get("cloud_api_key", "")).strip()
    cloud_model = str(data.get("cloud_model", "")).strip()

    voice_id = str(data.get("voice_id", "en_US-lessac-medium")).strip()
    if voice_id not in _VOICE_IDS:
        voice_id = "en_US-lessac-medium"
    voice_model_path = f"models/piper/{voice_id}.onnx"

    wifi_ssid = str(data.get("wifi_ssid", "")).strip()
    wifi_password = str(data.get("wifi_password", "")).strip()
    hostname = str(data.get("hostname", "omnibot-zero")).strip() or "omnibot-zero"

    # Build openrouter section (used for all cloud providers for now)
    openrouter_cfg: Optional[Dict] = None
    if cloud_provider != "none" and cloud_api_key:
        openrouter_cfg = {
            "api_key": cloud_api_key,
            "model": cloud_model or "google/gemini-2.0-flash-lite:free",
            "provider": cloud_provider,
        }

    return {
        "bud": {
            "id": bud_id,
            "name": bud_name,
            "system_prompt": bud_prompt,
            "ui_accent_color": bud_color,
        },
        "hardware": {"lcd": "?", "audio": "?", "battery": "?", "buttons": "?"},
        "connectivity": {"wifi": "?", "ollama": None},
        "openrouter": openrouter_cfg,
        "stt": {"engine": "faster-whisper", "model_size": "tiny.en", "sample_rate": 16000},
        "tts": {
            "engine": "piper",
            "profile": "cyberpunk",
            "model_path": voice_model_path,
        },
        "ai": {
            "prefer_local_first": True,
            "offline_fallback_model": f"models/{offline_model_file}",
        },
        "network": {"ssid": wifi_ssid, "password": wifi_password, "hostname": hostname},
        "dashboard": {"enabled": True, "host": "127.0.0.1", "port": 8080},
        "ota": {"enabled": True, "remote": "origin"},
        "sync": {"enabled": False, "port": 8091, "service_type": "_omnibot._tcp.local."},
    }
