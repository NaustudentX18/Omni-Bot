"""Safety-critical path tests for final deployment readiness."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from jarvis_bud.audit import AuditLogger
from jarvis_bud.hardware.tts import SpeechSynth
from jarvis_bud.reporting import _find_usb_mount
from jarvis_bud.reporting import ReportBuilder, TimelineEvent
from jarvis_bud.tools import ToolRunner
from jarvis_bud.voice import VoiceCommandParser


def test_audit_chain_detects_tampering():
    with tempfile.TemporaryDirectory() as tmp:
        ledger = Path(tmp) / "audit.jsonl"
        logger = AuditLogger(str(ledger))
        logger.log_event("boot", {"ok": True})
        logger.log_event("voice.command", {"command": "status"})
        assert logger.verify_chain() is True

        lines = ledger.read_text(encoding="utf-8").strip().splitlines()
        first = json.loads(lines[0])
        first["payload"]["ok"] = False  # tamper after hash was generated
        lines[0] = json.dumps(first)
        ledger.write_text("\n".join(lines) + "\n", encoding="utf-8")
        assert logger.verify_chain() is False


def test_toolrunner_high_risk_needs_confirmation():
    with tempfile.TemporaryDirectory() as tmp:
        audit = AuditLogger(str(Path(tmp) / "audit.jsonl"))
        runner = ToolRunner(
            audit=audit,
            dry_run=True,
            risk_confirm_threshold=6,
            confirm_callback=lambda _tool, _risk: False,
        )
        result = runner.sqlmap("http://example.com")
        assert result.ok is False
        assert result.skipped is True
        assert "confirmation required" in result.stderr


def test_toolrunner_stop_all_kills_tracked_processes():
    with tempfile.TemporaryDirectory() as tmp:
        audit = AuditLogger(str(Path(tmp) / "audit.jsonl"))
        runner = ToolRunner(audit=audit, dry_run=False, confirm_callback=lambda _t, _r: True, drop_privileges=False)
        proc = subprocess.Popen(["sleep", "30"], start_new_session=True)
        try:
            runner._tracked[proc.pid] = proc
            stopped = runner.stop_all(reason="pytest")
            assert proc.pid in stopped["stopped_pids"]
        finally:
            if proc.poll() is None:
                proc.kill()


def test_voice_parser_expanded_commands():
    parser = VoiceCommandParser()
    assert parser.parse("status").command == "status"
    assert parser.parse("target add 10.0.0.5").args["target"] == "10.0.0.5"
    assert parser.parse("crack wifi").command == "crack_wifi"
    assert parser.parse("god mode").command == "god_mode"
    assert parser.parse("make legendary").command == "make_legendary"


def test_speech_synth_piper_path_avoids_shell_execution():
    synth = SpeechSynth()
    synth.piper_bin = "/usr/bin/piper"
    synth.aplay_bin = "/usr/bin/aplay"
    synth.espeak_bin = None

    class _DummyProc:
        def __init__(self, with_stdout: bool = False):
            self.returncode = 0
            self.stdout = MagicMock() if with_stdout else None
            self.input = None

        def communicate(self, input=None, timeout=None):
            self.input = input
            return (b"", b"")

        def wait(self, timeout=None):
            return self.returncode

    piper_proc = _DummyProc(with_stdout=True)
    aplay_proc = _DummyProc(with_stdout=False)
    popen_calls = []

    def _fake_popen(args, **kwargs):
        popen_calls.append((args, kwargs))
        return piper_proc if len(popen_calls) == 1 else aplay_proc

    message = 'hello $(touch /tmp/pwned); `id` | whoami & "quote"'
    with patch("jarvis_bud.hardware.tts.subprocess.Popen", side_effect=_fake_popen), patch(
        "jarvis_bud.hardware.tts.subprocess.run"
    ) as run_mock:
        assert synth.speak(message) is True
        run_mock.assert_not_called()

    assert popen_calls[0][0] == [synth.piper_bin, "--model", synth.piper_model, "--output-raw"]
    assert popen_calls[1][0] == [synth.aplay_bin, "-q", "-r", "22050", "-f", "S16_LE", "-t", "raw", "-"]
    assert "shell" not in popen_calls[0][1]
    assert "shell" not in popen_calls[1][1]
    assert piper_proc.input == message.encode("utf-8")
    piper_proc.stdout.close.assert_called_once()


def test_find_usb_mount_prefers_nested_device_directory():
    with tempfile.TemporaryDirectory() as tmp:
        media_root = Path(tmp) / "media"
        user_dir = media_root / "pi"
        device_dir = user_dir / "USB_DRIVE"
        device_dir.mkdir(parents=True)

        mount = _find_usb_mount([media_root])

        assert mount == device_dir


def test_report_builder_escapes_event_and_detail_html():
    builder = ReportBuilder()
    malicious_event = "brain.<img src=x onerror=alert(1)>"
    payload = {"prompt_preview": "<img src=x onerror=alert(1)>", "risk": 7}
    builder.events.append(
        TimelineEvent(
            ts=1.0,
            event=malicious_event,
            detail=json.dumps(payload, ensure_ascii=True),
            severity=7,
        )
    )

    html_report = builder.to_html()

    assert "<img src=x onerror=alert(1)>" not in html_report
    assert "&lt;img src=x onerror=alert(1)&gt;" in html_report
