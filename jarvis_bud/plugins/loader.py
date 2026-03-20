"""Hot-loadable plugin system for Jarvis-Bud.

Scans a directory for ``*.py`` plugin modules, imports them, and calls their
``register(ctx)`` function.  Plugins can add voice commands or tool wrappers
without restarting the main application.
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import sys
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class PluginTool:
    """A tool registered by a plugin."""

    name: str
    risk: int
    handler: Callable[..., str]
    description: str = ""
    plugin_name: str = ""


@dataclass
class PluginVoiceCommand:
    """A voice command registered by a plugin."""

    phrase: str
    handler: Callable[[Dict[str, str]], str]
    risk: int = 1
    plugin_name: str = ""


class PluginContext:
    """Context passed to each plugin's ``register()`` function.

    Provides decorators and methods to register tools and voice commands.
    """

    def __init__(self, plugin_name: str = ""):
        self.plugin_name = plugin_name
        self.tools: List[PluginTool] = []
        self.voice_commands: List[PluginVoiceCommand] = []

    def add_tool(self, name: str, risk: int = 1, description: str = ""):
        """Decorator to register a tool handler."""

        def decorator(func: Callable[..., str]) -> Callable[..., str]:
            self.tools.append(
                PluginTool(
                    name=name,
                    risk=risk,
                    handler=func,
                    description=description,
                    plugin_name=self.plugin_name,
                )
            )
            return func

        return decorator

    def add_voice_command(self, phrase: str, risk: int = 1):
        """Decorator to register a voice command handler."""

        def decorator(func: Callable[[Dict[str, str]], str]) -> Callable[[Dict[str, str]], str]:
            self.voice_commands.append(
                PluginVoiceCommand(
                    phrase=phrase.lower().strip(),
                    handler=func,
                    risk=risk,
                    plugin_name=self.plugin_name,
                )
            )
            return func

        return decorator


@dataclass
class LoadedPlugin:
    """Metadata about a loaded plugin."""

    name: str
    version: str
    path: str
    tools: List[str] = field(default_factory=list)
    voice_commands: List[str] = field(default_factory=list)
    error: Optional[str] = None


class PluginLoader:
    """Discovers, loads, and manages plugins."""

    def __init__(self, plugin_dirs: Optional[List[str]] = None):
        self.plugin_dirs = plugin_dirs or [str(Path(__file__).parent)]
        self._plugins: Dict[str, LoadedPlugin] = {}
        self._tools: Dict[str, PluginTool] = {}
        self._voice_commands: List[PluginVoiceCommand] = []

    @property
    def plugins(self) -> Dict[str, LoadedPlugin]:
        return dict(self._plugins)

    @property
    def tools(self) -> Dict[str, PluginTool]:
        return dict(self._tools)

    @property
    def voice_commands(self) -> List[PluginVoiceCommand]:
        return list(self._voice_commands)

    def scan_and_load(self) -> List[LoadedPlugin]:
        """Scan plugin directories and load all valid plugins."""
        results: List[LoadedPlugin] = []
        for plugin_dir in self.plugin_dirs:
            pdir = Path(plugin_dir)
            if not pdir.is_dir():
                continue
            for py_file in sorted(pdir.glob("*.py")):
                if py_file.name.startswith("_") or py_file.name == "loader.py":
                    continue
                result = self._load_plugin(py_file)
                results.append(result)
        return results

    def _load_plugin(self, path: Path) -> LoadedPlugin:
        """Load a single plugin module."""
        module_name = f"jarvis_bud.plugins.{path.stem}"
        try:
            spec = importlib.util.spec_from_file_location(module_name, str(path))
            if not spec or not spec.loader:
                return LoadedPlugin(name=path.stem, version="?", path=str(path), error="Invalid module spec")

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            plugin_name = getattr(module, "PLUGIN_NAME", path.stem)
            plugin_version = getattr(module, "PLUGIN_VERSION", "0.1")

            register_fn = getattr(module, "register", None)
            if not callable(register_fn):
                return LoadedPlugin(
                    name=plugin_name,
                    version=plugin_version,
                    path=str(path),
                    error="No register() function found",
                )

            ctx = PluginContext(plugin_name=plugin_name)
            register_fn(ctx)

            for tool in ctx.tools:
                self._tools[tool.name] = tool
            self._voice_commands.extend(ctx.voice_commands)

            loaded = LoadedPlugin(
                name=plugin_name,
                version=plugin_version,
                path=str(path),
                tools=[t.name for t in ctx.tools],
                voice_commands=[vc.phrase for vc in ctx.voice_commands],
            )
            self._plugins[plugin_name] = loaded
            print(f"🔌 Plugin loaded: {plugin_name} v{plugin_version} "
                  f"({len(ctx.tools)} tools, {len(ctx.voice_commands)} commands)")
            return loaded

        except Exception as exc:
            error_msg = f"{type(exc).__name__}: {exc}"
            print(f"⚠️  Plugin load failed ({path.name}): {error_msg}")
            return LoadedPlugin(name=path.stem, version="?", path=str(path), error=error_msg)

    def reload_all(self) -> List[LoadedPlugin]:
        """Clear all plugins and reload from disk."""
        self._plugins.clear()
        self._tools.clear()
        self._voice_commands.clear()
        return self.scan_and_load()

    def match_voice_command(self, text: str) -> Optional[Tuple[PluginVoiceCommand, Dict[str, str]]]:
        """Try to match input text to a plugin voice command."""
        normalized = " ".join(text.lower().strip().split())
        for vc in self._voice_commands:
            if vc.phrase in normalized:
                return vc, {"text": text}
        return None

    def run_tool(self, tool_name: str, *args: Any, **kwargs: Any) -> Optional[str]:
        """Execute a plugin tool by name."""
        tool = self._tools.get(tool_name)
        if not tool:
            return None
        try:
            return tool.handler(*args, **kwargs)
        except Exception as exc:
            return f"Plugin tool error: {exc}"
