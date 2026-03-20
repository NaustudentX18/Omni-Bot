"""Example plugin demonstrating the Jarvis-Bud plugin system.

This plugin adds a 'system info' voice command and a 'sysinfo' tool.
"""

from __future__ import annotations

import platform
import os

PLUGIN_NAME = "sysinfo"
PLUGIN_VERSION = "1.0"


def register(ctx):
    """Register tools and voice commands with the plugin context."""

    @ctx.add_voice_command("system info", risk=1)
    def _system_info(args):
        uname = platform.uname()
        return (
            f"System: {uname.system} {uname.release} | "
            f"Machine: {uname.machine} | "
            f"Python: {platform.python_version()}"
        )

    @ctx.add_tool("sysinfo", risk=1, description="Show system information")
    def _sysinfo_tool(target=None):
        load = os.getloadavg()
        return (
            f"Host: {platform.node()} | "
            f"Arch: {platform.machine()} | "
            f"Load: {load[0]:.2f} {load[1]:.2f} {load[2]:.2f}"
        )
