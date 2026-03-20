"""Example hot-reload plugin for custom commands."""

from __future__ import annotations


def _voice_neon_status(app, text: str) -> str:
    snapshot = app.get_status_snapshot()
    return (
        "Neon status pulse: "
        f"bud={snapshot['current_bud']}, mode={snapshot['connectivity_mode']}, "
        f"targets={len(snapshot['targets'])}"
    )


def _tool_mark_target(target: str) -> str:
    return f"plugin-marked:{target}"


def register():
    return {
        "voice_commands": [
            {
                "command": "neon_status",
                "patterns": [r"\bneon status\b", r"\bstatus pulse\b"],
                "handler": _voice_neon_status,
            }
        ],
        "tools": [{"name": "plugin_mark_target", "handler": _tool_mark_target}],
    }
