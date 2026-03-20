"""Plugin loader tests."""

from __future__ import annotations

from pathlib import Path

from jarvis_bud.audit import AuditLogger
from jarvis_bud.plugins.loader import PluginLoader


class _DummyTools:
    pass


class _DummyApp:
    def get_status_snapshot(self):
        return {"current_bud": "Fogo"}


def test_plugin_loader_handles_voice_command(tmp_path: Path):
    plugin_dir = tmp_path / "plugins"
    plugin_dir.mkdir(parents=True)
    plugin_file = plugin_dir / "echo_plugin.py"
    plugin_file.write_text(
        """
def _voice(app, text):
    return "echo:" + text

def register():
    return {"voice_commands": [{"command": "echo", "patterns": [r"echo"], "handler": _voice}], "tools": []}
""".strip(),
        encoding="utf-8",
    )

    audit = AuditLogger(str(tmp_path / "audit.jsonl"))
    loader = PluginLoader(audit=audit, tool_runner=_DummyTools(), plugin_dir=str(plugin_dir))
    reply = loader.handle_voice_text("echo test", _DummyApp())
    assert reply == "echo:echo test"
