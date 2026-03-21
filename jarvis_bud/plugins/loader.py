"""Tiny hot-reload plugin loader for Jarvis-Bud."""

from __future__ import annotations

import importlib.util
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

from jarvis_bud.audit import AuditLogger


@dataclass
class PluginVoiceCommand:
    command: str
    patterns: list[re.Pattern[str]]
    handler: Callable[..., str]
    plugin_name: str


@dataclass
class LoadedPlugin:
    name: str
    path: Path
    mtime: float
    module: ModuleType
    voice_commands: list[PluginVoiceCommand]
    tools: dict[str, Callable[..., Any]]


class PluginLoader:
    """Discover and hot-reload plugins from jarvis_bud/plugins."""

    def __init__(
        self, audit: AuditLogger, tool_runner: Any, plugin_dir: str = "jarvis_bud/plugins"
    ):
        self.audit = audit
        self.tool_runner = tool_runner
        self.plugin_dir = Path(plugin_dir)
        self.plugin_dir.mkdir(parents=True, exist_ok=True)
        self._plugins: dict[str, LoadedPlugin] = {}
        self.reload_if_needed(force=True)

    @property
    def plugin_count(self) -> int:
        return len(self._plugins)

    def _iter_plugin_files(self) -> list[Path]:
        files = []
        for path in sorted(self.plugin_dir.glob("*.py")):
            if path.name in {"__init__.py", "loader.py"}:
                continue
            files.append(path)
        return files

    def _import_module(self, plugin_file: Path) -> ModuleType | None:
        mod_name = f"jarvis_bud_dynamic_plugin_{plugin_file.stem}"
        spec = importlib.util.spec_from_file_location(mod_name, plugin_file)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _parse_plugin(self, name: str, path: Path, module: ModuleType) -> LoadedPlugin:
        register = getattr(module, "register", None)
        voice_commands: list[PluginVoiceCommand] = []
        tools: dict[str, Callable[..., Any]] = {}
        if callable(register):
            payload = register() or {}
            for command in payload.get("voice_commands", []):
                handler = command.get("handler")
                if not callable(handler):
                    continue
                compiled = [
                    re.compile(pattern, re.IGNORECASE)
                    for pattern in command.get("patterns", [])
                    if pattern
                ]
                voice_commands.append(
                    PluginVoiceCommand(
                        command=command.get("command", f"{name}_command"),
                        patterns=compiled,
                        handler=handler,
                        plugin_name=name,
                    )
                )
            for tool in payload.get("tools", []):
                tool_name = tool.get("name", "").strip()
                handler = tool.get("handler")
                if tool_name and callable(handler):
                    tools[tool_name] = handler
        for tool_name, handler in tools.items():
            setattr(self.tool_runner, tool_name, handler)
        return LoadedPlugin(
            name=name,
            path=path,
            mtime=path.stat().st_mtime,
            module=module,
            voice_commands=voice_commands,
            tools=tools,
        )

    def reload_if_needed(self, force: bool = False) -> bool:
        changed = False
        for plugin_file in self._iter_plugin_files():
            name = plugin_file.stem
            mtime = plugin_file.stat().st_mtime
            cached = self._plugins.get(name)
            if not force and cached and mtime <= cached.mtime:
                continue
            try:
                module = self._import_module(plugin_file)
                if module is None:
                    continue
                loaded = self._parse_plugin(name, plugin_file, module)
                self._plugins[name] = loaded
                self.audit.log_event(
                    "plugin.loaded",
                    {
                        "plugin": name,
                        "voice_commands": len(loaded.voice_commands),
                        "tools": list(loaded.tools.keys()),
                    },
                )
                changed = True
            except Exception as exc:
                self.audit.log_event("plugin.error", {"plugin": name, "error": str(exc)})
        return changed

    def handle_voice_text(self, text: str, app: Any) -> str | None:
        self.reload_if_needed(force=False)
        normalized = text.strip()
        if not normalized:
            return None
        for plugin in self._plugins.values():
            for command in plugin.voice_commands:
                if any(pattern.search(normalized) for pattern in command.patterns):
                    try:
                        self.audit.log_event(
                            "plugin.voice.invoke",
                            {"plugin": plugin.name, "command": command.command},
                        )
                        return command.handler(app=app, text=normalized)
                    except Exception as exc:
                        self.audit.log_event(
                            "plugin.voice.error", {"plugin": plugin.name, "error": str(exc)}
                        )
                        return f"Plugin {plugin.name} failed: {exc}"
        return None
