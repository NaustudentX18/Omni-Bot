"""Regression tests for first-run stability and routing behavior."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jarvis_bud.config import ConfigManager
from jarvis_bud.core.buds import BudManager
from jarvis_bud.main import JarvisBud


class _AlwaysAvailableOllama:
    """Small test double that should never be rescanned."""

    @property
    def is_available(self) -> bool:
        return True

    def scan(self):
        raise AssertionError("scan() should not be called when already available")

    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        return "python docker success"


class _BatteryProbe:
    """Counts status fetches to validate caching behavior."""

    def __init__(self):
        self.calls = 0

    def get_status(self):
        self.calls += 1
        return {"percentage": 42, "charging": True}


class RegressionTests(unittest.TestCase):
    def test_get_display_dict_allows_null_openrouter(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            manager = ConfigManager(str(config_path))
            manager._config = {
                "bud": {"id": "fogo", "name": "Fogo", "system_prompt": "hello"},
                "openrouter": None,
            }

            display = manager.get_display_dict()

            self.assertIn("openrouter", display)
            self.assertIsNone(display["openrouter"])
            self.assertTrue(manager.is_configured())

    def test_set_handles_legacy_non_dict_branch(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            manager = ConfigManager(str(config_path))
            manager._config = {"bud": "legacy-string"}

            manager.set("bud.name", "Fogo")

            self.assertEqual(manager.get("bud.name"), "Fogo")

    def test_battery_snapshot_uses_refresh_interval_cache(self):
        app = JarvisBud(config_path="/tmp/nonexistent-jarvis-config.json")
        battery = _BatteryProbe()
        app.battery = battery

        app._refresh_battery_snapshot(force=True)
        app._refresh_battery_snapshot(force=False)

        self.assertEqual(battery.calls, 1)
        self.assertEqual(app._battery_snapshot["percentage"], 42)
        self.assertTrue(app._battery_snapshot["charging"])

    def test_bud_manager_skips_rescan_when_local_is_online(self):
        manager = BudManager(ollama=_AlwaysAvailableOllama(), openrouter_key=None)

        response = manager.generate_response("give me build steps")

        self.assertIn("🐍 python", response)
        self.assertIn("🐳 docker", response)


if __name__ == "__main__":
    unittest.main()
