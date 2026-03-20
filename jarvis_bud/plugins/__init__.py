"""Plugin system for extending Jarvis-Bud with custom tools and voice commands.

Plugins are Python modules placed in ``jarvis_bud/plugins/`` (or a custom
directory). Each plugin module must expose a ``register(ctx)`` function that
receives a :class:`PluginContext` and uses it to add tools or voice commands.

Example plugin (``jarvis_bud/plugins/hello_plugin.py``)::

    PLUGIN_NAME = "hello"
    PLUGIN_VERSION = "1.0"

    def register(ctx):
        @ctx.add_voice_command("say hello")
        def _hello(args):
            return "Hello from the plugin system!"

        @ctx.add_tool("hello_tool", risk=1)
        def _tool(target):
            return f"Hello tool called with: {target}"
"""

from .loader import PluginLoader, PluginContext

__all__ = ["PluginLoader", "PluginContext"]
