"""Tests for all 6 new roadmap features: STT, TTS, Web Dashboard, OTA, Plugins, Sync."""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ── Feature 1: STT ──────────────────────────────────────────────────────────

class TestSpeechToText:
    def test_stt_import_and_fallback(self):
        """STT module loads even without faster-whisper; reports unavailable."""
        from jarvis_bud.hardware.stt import SpeechToText

        with patch.dict("sys.modules", {"faster_whisper": None}):
            stt = SpeechToText.__new__(SpeechToText)
            stt._model = None
            stt._available = False
            assert stt.is_available is False
            assert stt.transcribe_bytes(b"\x00" * 100) == ""

    def test_stt_transcribe_empty_audio(self):
        from jarvis_bud.hardware.stt import SpeechToText

        stt = SpeechToText.__new__(SpeechToText)
        stt._model = None
        stt._available = False
        assert stt.transcribe_bytes(b"") == ""

    def test_stt_ram_estimate_no_model(self):
        from jarvis_bud.hardware.stt import SpeechToText

        stt = SpeechToText.__new__(SpeechToText)
        stt._model = None
        stt._available = False
        assert stt.estimate_ram_mb() == 0.0

    def test_stt_exported_from_hardware(self):
        from jarvis_bud.hardware import SpeechToText
        assert SpeechToText is not None


# ── Feature 2: TTS ──────────────────────────────────────────────────────────

class TestSpeechSynthEnhanced:
    def test_tts_voice_styles(self):
        from jarvis_bud.hardware.tts import SpeechSynth

        synth = SpeechSynth(voice_style="cyberpunk")
        assert "lessac" in synth.piper_model

        synth.set_voice("british")
        assert synth.voice_style == "british"

    def test_tts_backend_detection(self):
        from jarvis_bud.hardware.tts import SpeechSynth

        synth = SpeechSynth()
        synth.piper_bin = None
        synth.aplay_bin = None
        synth.espeak_bin = None
        assert synth.backend == "none"

        synth.espeak_bin = "/usr/bin/espeak-ng"
        assert synth.backend == "espeak"

        synth.piper_bin = "/usr/bin/piper"
        synth.aplay_bin = "/usr/bin/aplay"
        assert synth.backend == "piper"

    def test_tts_speak_empty(self):
        from jarvis_bud.hardware.tts import SpeechSynth

        synth = SpeechSynth()
        assert synth.speak("") is False
        assert synth.speak("   ") is False

    def test_tts_rate_clamping(self):
        from jarvis_bud.hardware.tts import SpeechSynth

        synth = SpeechSynth(speaking_rate=999.0)
        assert synth.speaking_rate == 2.0

        synth2 = SpeechSynth(speaking_rate=-5.0)
        assert synth2.speaking_rate == 0.5

    def test_tts_piper_no_shell_injection(self):
        """Verify that Piper TTS never uses shell=True."""
        from jarvis_bud.hardware.tts import SpeechSynth

        synth = SpeechSynth()
        synth.piper_bin = "/usr/bin/piper"
        synth.aplay_bin = "/usr/bin/aplay"
        synth.espeak_bin = None

        popen_calls = []

        class _FakeStdout:
            closed = False
            def close(self): self.closed = True
            def fileno(self): return 1

        class _FakeStdin:
            writes = []
            closed = False
            def write(self, d): self.writes.append(d); return len(d)
            def close(self): self.closed = True

        class _FakeProc:
            returncode = 0
            stdout = _FakeStdout()
            stdin = _FakeStdin()
            def wait(self, timeout=None): pass

        def _fake_popen(args, **kwargs):
            popen_calls.append((args, kwargs))
            return _FakeProc()

        with patch("jarvis_bud.hardware.tts.subprocess.Popen", side_effect=_fake_popen):
            synth.speak("hello $(rm -rf /)")

        assert len(popen_calls) == 2
        assert "shell" not in popen_calls[0][1]
        assert "shell" not in popen_calls[1][1]


# ── Feature 3: Web Dashboard ────────────────────────────────────────────────

class TestWebDashboard:
    def test_dashboard_creates_app(self):
        from jarvis_bud.web.dashboard import create_app

        app = create_app()
        assert app is not None
        client = app.test_client()
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"NXTGENAI" in resp.data

    def test_dashboard_status_api(self):
        from jarvis_bud.web.dashboard import create_app

        app = create_app()
        client = app.test_client()
        resp = client.get("/api/status")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert "uptime_s" in data
        assert "version" in data

    def test_dashboard_config_api(self):
        from jarvis_bud.web.dashboard import create_app

        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = os.path.join(tmp, "config.json")
            app = create_app(config_path=cfg_path)
            client = app.test_client()

            resp = client.get("/api/config")
            assert resp.status_code == 200

            resp = client.post(
                "/api/config",
                data=json.dumps({"bud": {"id": "fogo"}}),
                content_type="application/json",
            )
            assert resp.status_code == 200
            assert json.loads(resp.data)["ok"] is True

            with open(cfg_path) as f:
                saved = json.load(f)
            assert saved["bud"]["id"] == "fogo"

    def test_dashboard_emergency_stop_no_jarvis(self):
        from jarvis_bud.web.dashboard import create_app

        app = create_app()
        client = app.test_client()
        resp = client.post("/api/emergency-stop")
        assert resp.status_code == 503

    def test_dashboard_audit_api(self):
        from jarvis_bud.web.dashboard import create_app

        with tempfile.TemporaryDirectory() as tmp:
            audit_path = os.path.join(tmp, "audit.jsonl")
            Path(audit_path).write_text(
                json.dumps({"ts": 1.0, "event": "test", "payload": {}}) + "\n"
            )
            app = create_app(audit_path=audit_path)
            client = app.test_client()
            resp = client.get("/api/audit")
            assert resp.status_code == 200
            data = json.loads(resp.data)
            assert len(data) == 1
            assert data[0]["event"] == "test"

    def test_dashboard_ram_api(self):
        from jarvis_bud.web.dashboard import create_app

        app = create_app()
        client = app.test_client()
        resp = client.get("/api/ram")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert "peak_rss_mb" in data


# ── Feature 4: OTA Updater ──────────────────────────────────────────────────

class TestOTAUpdater:
    def test_updater_get_version(self):
        from jarvis_bud.updater import OTAUpdater

        updater = OTAUpdater(repo_dir="/workspace")
        version = updater.get_current_version()
        assert "@" in version

    def test_updater_check_no_remote(self):
        """check_for_updates gracefully handles missing remote."""
        from jarvis_bud.updater import OTAUpdater

        with tempfile.TemporaryDirectory() as tmp:
            updater = OTAUpdater(repo_dir=tmp)
            result = updater.check_for_updates()
            assert isinstance(result, dict)

    def test_updater_apply_without_confirm(self):
        from jarvis_bud.updater import OTAUpdater

        updater = OTAUpdater(repo_dir="/workspace", auto_confirm=False)
        result = updater.apply_update()
        assert result["success"] is False
        assert "No confirmation" in result["message"]

    def test_updater_apply_declined(self):
        from jarvis_bud.updater import OTAUpdater

        updater = OTAUpdater(repo_dir="/workspace", auto_confirm=False)
        result = updater.apply_update(confirm_callback=lambda: False)
        assert result["success"] is False
        assert "declined" in result["message"]

    def test_updater_changelog(self):
        from jarvis_bud.updater import OTAUpdater

        updater = OTAUpdater(repo_dir="/workspace")
        log = updater.get_changelog(max_entries=3)
        assert isinstance(log, str)


# ── Feature 5: Plugin System ────────────────────────────────────────────────

class TestPluginSystem:
    def test_plugin_loader_discovers_example(self):
        from jarvis_bud.plugins import PluginLoader

        loader = PluginLoader()
        results = loader.scan_and_load()
        names = [r.name for r in results if not r.error]
        assert "sysinfo" in names

    def test_plugin_context_add_tool(self):
        from jarvis_bud.plugins.loader import PluginContext

        ctx = PluginContext(plugin_name="test")

        @ctx.add_tool("my_tool", risk=2)
        def _handler(target):
            return f"ran on {target}"

        assert len(ctx.tools) == 1
        assert ctx.tools[0].name == "my_tool"
        assert ctx.tools[0].handler("10.0.0.1") == "ran on 10.0.0.1"

    def test_plugin_context_add_voice_command(self):
        from jarvis_bud.plugins.loader import PluginContext

        ctx = PluginContext(plugin_name="test")

        @ctx.add_voice_command("do something", risk=3)
        def _vc(args):
            return "done"

        assert len(ctx.voice_commands) == 1
        assert ctx.voice_commands[0].phrase == "do something"
        assert ctx.voice_commands[0].handler({}) == "done"

    def test_plugin_loader_match_voice(self):
        from jarvis_bud.plugins import PluginLoader

        loader = PluginLoader()
        loader.scan_and_load()
        match = loader.match_voice_command("show me system info")
        assert match is not None
        vc, args = match
        result = vc.handler(args)
        assert "System" in result or "Python" in result

    def test_plugin_loader_run_tool(self):
        from jarvis_bud.plugins import PluginLoader

        loader = PluginLoader()
        loader.scan_and_load()
        result = loader.run_tool("sysinfo")
        assert result is not None
        assert "Host" in result or "Arch" in result

    def test_plugin_loader_reload(self):
        from jarvis_bud.plugins import PluginLoader

        loader = PluginLoader()
        loader.scan_and_load()
        assert len(loader.plugins) > 0
        loader.reload_all()
        assert len(loader.plugins) > 0

    def test_plugin_loader_bad_plugin(self):
        """Loading a bad plugin file doesn't crash the loader."""
        from jarvis_bud.plugins import PluginLoader

        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "broken_plugin.py"
            bad.write_text("raise RuntimeError('broken')\n")
            loader = PluginLoader(plugin_dirs=[tmp])
            results = loader.scan_and_load()
            assert len(results) == 1
            assert results[0].error is not None

    def test_plugin_loader_missing_register(self):
        from jarvis_bud.plugins import PluginLoader

        with tempfile.TemporaryDirectory() as tmp:
            no_reg = Path(tmp) / "no_register.py"
            no_reg.write_text("PLUGIN_NAME = 'nope'\n")
            loader = PluginLoader(plugin_dirs=[tmp])
            results = loader.scan_and_load()
            assert results[0].error is not None
            assert "register" in results[0].error


# ── Feature 6: Multi-Device Sync ────────────────────────────────────────────

class TestDeviceSync:
    def test_sync_import(self):
        from jarvis_bud.sync import DeviceSync
        assert DeviceSync is not None

    def test_sync_init(self):
        from jarvis_bud.sync import DeviceSync

        sync = DeviceSync(node_name="test-node", sync_port=19876)
        assert sync.node_name == "test-node"
        assert sync.sync_port == 19876
        assert sync.is_available is False

    def test_sync_share_targets(self):
        from jarvis_bud.sync import DeviceSync

        sync = DeviceSync()
        sync.share_targets(["192.168.1.0/24", "10.0.0.0/8"])
        assert len(sync._shared_targets) == 2

    def test_sync_peers_empty(self):
        from jarvis_bud.sync import DeviceSync

        sync = DeviceSync()
        assert sync.peers == []

    def test_sync_get_local_ip(self):
        from jarvis_bud.sync import DeviceSync

        ip = DeviceSync._get_local_ip()
        assert isinstance(ip, str)
        assert "." in ip


# ── Integration: JarvisBud with new features ────────────────────────────────

class TestJarvisBudIntegration:
    def test_jarvis_has_stt(self):
        from jarvis_bud.main import JarvisBud

        app = JarvisBud(config_path="/tmp/nonexistent-config-test.json")
        assert hasattr(app, "stt")

    def test_transcribe_uses_env_override(self):
        from jarvis_bud.main import JarvisBud

        app = JarvisBud(config_path="/tmp/nonexistent-config-test.json")
        with patch.dict(os.environ, {"NXTGENAI_FAKE_STT": "god mode"}):
            result = app._transcribe_audio(b"\x00" * 100)
            assert result == "god mode"

    def test_transcribe_falls_back_to_status(self):
        from jarvis_bud.main import JarvisBud

        app = JarvisBud(config_path="/tmp/nonexistent-config-test.json")
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("NXTGENAI_FAKE_STT", None)
            result = app._transcribe_audio(b"")
            assert result == "status"
