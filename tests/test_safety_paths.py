"""Safety-critical path tests for final deployment readiness."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from jarvis_bud.audit import AuditLogger
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
