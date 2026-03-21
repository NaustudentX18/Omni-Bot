"""First-Boot Setup Wizard for Jarvis-Bud."""

import json
import os
import sys
import time
from typing import Any

from jarvis_bud.core import LocalOllamaClient
from jarvis_bud.hardware import ST7789Display
from jarvis_bud.ui import FrameRenderer


class SetupWizard:
    """
    Interactive 4-step setup wizard for first-boot configuration.
    Guides user through hardware check, connectivity, personality selection, and API setup.
    """

    STEPS = {
        1: "Hardware Check 🔧",
        2: "Connectivity 📡",
        3: "Pick Your Bud 🤝",
        4: "API Configuration 🔑",
    }

    def __init__(
        self, config_path: str = "config/config.json", buds_path: str = "jarvis_bud/buds.json"
    ):
        """Initialize setup wizard.

        Args:
            config_path: Path to save config
            buds_path: Path to buds.json
        """
        self.config_path = config_path
        self.buds_path = buds_path
        self.config: dict[str, Any] = {}
        self.buds: dict[str, Any] = {}
        self.display: ST7789Display | None = None
        self.renderer: FrameRenderer | None = None

        self._load_buds()

    def _load_buds(self):
        """Load available Buds from buds.json."""
        try:
            with open(self.buds_path) as f:
                data = json.load(f)
                self.buds = {bud["id"]: bud for bud in data.get("buds", [])}

                if "fogo" not in self.buds:
                    self.buds["fogo"] = {
                        "id": "fogo",
                        "name": "Fogo",
                        "emoji": "🐐💻",
                        "description": "Creative Python + Docker + 3D printing expert",
                        "system_prompt": (
                            "You are Fogo, a creative and proactive technical AI. "
                            "Expert in Python, Docker, Bambu Lab P1S, and OrcaSlicer. "
                            "You give punchy hacker-ready advice with technical emoji."
                        ),
                        "ui_accent_color": "#00FF66",
                    }

                if "mango" not in self.buds:
                    self.buds["mango"] = {
                        "id": "mango",
                        "name": "Mango",
                        "emoji": "🥭",
                        "description": "Peace/love/vibe companion for calm planning",
                        "system_prompt": (
                            "You are Mango, a calm and uplifting AI guide. "
                            "Focus on peace, thoughtful guidance, and positive action."
                        ),
                        "ui_accent_color": "#FFC857",
                    }

                print(f"✅ Loaded {len(self.buds)} personalities from buds.json")
        except Exception as e:
            print(f"⚠️  Could not load buds: {e}")
            self.buds = {
                "fogo": {
                    "id": "fogo",
                    "name": "Fogo",
                    "emoji": "🐐💻",
                    "description": "Creative Python + Docker + 3D printing expert",
                    "system_prompt": "You are Fogo, a creative maker AI with hacker-ready advice.",
                    "ui_accent_color": "#00FF66",
                },
                "mango": {
                    "id": "mango",
                    "name": "Mango",
                    "emoji": "🥭",
                    "description": "Peace/love/vibe companion",
                    "system_prompt": "You are Mango, a calm and uplifting AI guide.",
                    "ui_accent_color": "#FFC857",
                },
            }

    def _init_lcd(self):
        """Try to initialize LCD renderer for wizard UI."""
        try:
            self.display = ST7789Display()
            if self.display.init():
                self.renderer = FrameRenderer()
        except Exception:
            self.display = None
            self.renderer = None

    def _render_lcd_step(
        self, step_number: int, step_title: str, content_lines: list, progress: float
    ):
        if not self.display or not self.renderer:
            return
        self.renderer.render_wizard_step(
            self.display,
            step_number=step_number,
            step_title=step_title,
            content_lines=content_lines,
            progress=progress,
        )

    def _meet_fogo_splash(self):
        if not self.display or not self.renderer:
            return
        self.renderer.render_message(
            self.display,
            title="Meet Fogo",
            message="Python + Docker + 3D Print Brain Online",
            emoji="🐐💻",
            message_type="success",
        )
        time.sleep(1.2)

    def should_run(self) -> bool:
        """Check if setup wizard should run (no config.json exists).

        Returns:
            True if wizard should run
        """
        return not os.path.exists(self.config_path)

    def run_interactive(self) -> bool:
        """Run the complete interactive setup wizard.

        Returns:
            True if successful
        """
        print("\n" + "=" * 60)
        print("🤖 JARVIS-BUD FIRST-BOOT WIZARD 🤖".center(60))
        print("=" * 60 + "\n")
        self._init_lcd()
        self._meet_fogo_splash()

        try:
            # Step 1: Hardware Check
            if not self._step_1_hardware_check():
                print("❌ Hardware check failed. Aborting setup.")
                return False

            # Step 2: Connectivity
            if not self._step_2_connectivity():
                print("⚠️  Connectivity issues, but continuing...")

            # Step 3: Personality Selection
            if not self._step_3_personality_selection():
                print("❌ Personality selection failed. Aborting setup.")
                return False

            # Step 4: API Configuration
            if not self._step_4_api_configuration():
                print("⚠️  API configuration incomplete, but continuing...")

            # Save configuration
            if self._save_config():
                print("\n✅ Setup complete! Jarvis-Bud is ready to go 🚀\n")
                return True
            else:
                print("❌ Failed to save configuration.")
                return False

        except KeyboardInterrupt:
            print("\n\n⚠️  Setup cancelled by user.")
            return False
        except Exception as e:
            print(f"\n❌ Setup error: {e}")
            return False

    def _step_1_hardware_check(self) -> bool:
        """Step 1: Hardware Check.

        Tests LCD, Audio Codec, and Battery.
        """
        print(f"\n{'Step 1: Hardware Check 🔧':^60}")
        print("-" * 60)
        self._render_lcd_step(
            1, "Hardware Check", ["Testing LCD", "Testing WM8960", "Testing PiSugar 3"], 0.25
        )

        from jarvis_bud.hardware import AudioCodec, Battery, ButtonHandler, ST7789Display

        results = {}

        # LCD Check
        print("\n📺 Testing ST7789 LCD Display...")
        try:
            lcd = ST7789Display()
            if lcd.init():
                results["lcd"] = "✅"
                print("   ✅ LCD initialized successfully")
            else:
                results["lcd"] = "⚠️"
                print("   ⚠️  LCD available in test mode")
        except Exception as e:
            results["lcd"] = "❌"
            print(f"   ❌ LCD error: {e}")

        # Audio Codec Check
        print("\n🎙️  Testing WM8960 Audio Codec...")
        try:
            audio = AudioCodec()
            if audio.init():
                level = audio.get_audio_level()
                results["audio"] = "✅"
                print(f"   ✅ Audio codec initialized (level: {level:.2f})")
            else:
                results["audio"] = "⚠️"
                print("   ⚠️  Audio available in test mode")
        except Exception as e:
            results["audio"] = "❌"
            print(f"   ❌ Audio error: {e}")

        # Battery Check
        print("\n🔋 Testing PiSugar 3 Battery...")
        try:
            battery = Battery()
            if battery.connect():
                status = battery.get_status()
                results["battery"] = "✅"
                charging_text = "(Charging)" if status.get("charging") else ""
                print(f"   ✅ Battery: {status['percentage']:.0f}% {charging_text}")
            else:
                results["battery"] = "⚠️"
                print("   ⚠️  Battery monitoring available without PiSugar socket")
        except Exception as e:
            results["battery"] = "❌"
            print(f"   ❌ Battery error: {e}")

        # GPIO Buttons Check
        print("\n🔘 Testing GPIO Buttons...")
        try:
            buttons = ButtonHandler()
            if buttons.is_initialized:
                results["buttons"] = "✅"
                print(
                    f"   ✅ Buttons initialized (A={buttons.button_a_gpio}, B={buttons.button_b_gpio})"
                )
            else:
                results["buttons"] = "⚠️"
                print("   ⚠️  Buttons in mock mode")
        except Exception as e:
            results["buttons"] = "❌"
            print(f"   ❌ Buttons error: {e}")

        self.config["hardware"] = results

        # Check if at least LCD and Audio work
        return results.get("lcd") in ["✅", "⚠️"] and results.get("audio") in ["✅", "⚠️"]

    def _step_2_connectivity(self) -> bool:
        """Step 2: Connectivity Check.

        Tests WiFi and local Ollama connectivity, then captures network credentials.
        """
        print(f"\n{'Step 2: Connectivity 📡':^60}")
        print("-" * 60)
        self._render_lcd_step(
            2, "Connectivity", ["Scanning LAN", "Finding Ollama", "Checking latency"], 0.5
        )

        connectivity: dict[str, Any] = {}

        # WiFi Check
        print("\n📳 Scanning WiFi networks...")
        try:
            import subprocess

            result = subprocess.run(["iwlist", "wlan0", "scanning"], capture_output=True, timeout=5)
            if result.returncode == 0:
                print("   ✅ WiFi scan successful")
                connectivity["wifi"] = "✅"
            else:
                print("   ⚠️  WiFi scan returned no output")
                connectivity["wifi"] = "⚠️"
        except Exception as e:
            print(f"   ⚠️  WiFi check disabled: {e}")
            connectivity["wifi"] = "⚠️"

        if sys.stdin.isatty():
            print("\n🧾 Network provisioning")
            ssid = input("   WiFi SSID (blank = skip): ").strip()
            password = input("   WiFi password (blank = skip): ").strip() if ssid else ""
            region = input("   WiFi region (default US): ").strip() or "US"
            hostname = (
                input("   Device hostname (default omnibot-zero): ").strip() or "omnibot-zero"
            )
        else:
            ssid = os.environ.get("NXTGENAI_WIFI_SSID", "").strip()
            password = os.environ.get("NXTGENAI_WIFI_PASSWORD", "").strip() if ssid else ""
            region = os.environ.get("NXTGENAI_WIFI_REGION", "US").strip() or "US"
            hostname = (
                os.environ.get("NXTGENAI_DEVICE_HOSTNAME", "omnibot-zero").strip() or "omnibot-zero"
            )

        self.config["network"] = {
            "ssid": ssid,
            "password": password,
            "region": region,
            "hostname": hostname,
        }

        # Pironman/Ollama Check with latency threshold
        print("\n🌐 Checking for local Ollama server...")
        try:
            candidates = [
                "192.168.1.100",
                "192.168.1.101",
                "192.168.1.110",
                "pironman",
                "naspi",
                "127.0.0.1",
            ]
            scanner = LocalOllamaClient(candidate_hosts=candidates, max_ping_ms=100.0)
            endpoint = scanner.scan()

            if endpoint:
                url = endpoint.base_url
                print(f"   ✅ Local Ollama found at {url} ({endpoint.latency_ms:.1f}ms)")
                connectivity["ollama"] = url
                connectivity["ollama_latency_ms"] = endpoint.latency_ms
                connectivity["ollama_model"] = scanner.model or "llama3"
            else:
                print("   ℹ️  No <100ms Ollama host found. Will use OpenRouter failover.")
                connectivity["ollama"] = None
                connectivity["ollama_latency_ms"] = None
                connectivity["ollama_model"] = None

        except Exception as e:
            print(f"   ℹ️  Ollama check skipped: {e}")
            connectivity["ollama"] = None
            connectivity["ollama_latency_ms"] = None
            connectivity["ollama_model"] = None

        self.config["connectivity"] = connectivity
        return True

    def _step_3_personality_selection(self) -> bool:
        """Step 3: Select Personality/Bud.

        User chooses from available personalities.
        """
        print(f"\n{'Step 3: Pick Your Bud 🤝':^60}")
        print("-" * 60)
        print("\nAvailable personalities:\n")
        self._render_lcd_step(
            3,
            "Pick Your Bud",
            ["Fogo: maker brain", "Mango: chill vibe", "Button B cycles later"],
            0.75,
        )

        bud_list = list(self.buds.values())

        for i, bud in enumerate(bud_list, 1):
            print(f"  {i}. {bud['name']}")
            print(f"     └─ {bud['description']}\n")

        if not sys.stdin.isatty():
            selected_bud = self.buds.get("fogo") or bud_list[0]
            self.config["bud"] = {
                "id": selected_bud["id"],
                "name": selected_bud["name"],
                "system_prompt": selected_bud["system_prompt"],
                "ui_accent_color": selected_bud["ui_accent_color"],
            }
            print(f"\n✅ Non-interactive mode: defaulted to {selected_bud['name']}\n")
            return True

        while True:
            try:
                choice = input(f"Select personality (1-{len(bud_list)}): ").strip()
                choice_idx = int(choice) - 1

                if 0 <= choice_idx < len(bud_list):
                    selected_bud = bud_list[choice_idx]
                    print(f"\n✅ Selected: {selected_bud['name']} {selected_bud['emoji']}\n")

                    self.config["bud"] = {
                        "id": selected_bud["id"],
                        "name": selected_bud["name"],
                        "system_prompt": selected_bud["system_prompt"],
                        "ui_accent_color": selected_bud["ui_accent_color"],
                    }
                    return True
                else:
                    print(f"❌ Please enter a number between 1 and {len(bud_list)}")
            except ValueError:
                print("❌ Invalid input. Please enter a number.")

    def _step_4_api_configuration(self) -> bool:
        """Step 4: API Configuration.

        User enters OpenRouter key and offline voice stack preferences.
        """
        print(f"\n{'Step 4: API Configuration 🔑':^60}")
        print("-" * 60)
        self._render_lcd_step(
            4,
            "API Setup",
            ["OpenRouter optional", "Gemini 2.0 Flash Lite", "Used for failover"],
            1.0,
        )

        print("\n🌐 OpenRouter Setup (Optional but recommended for mobile use)")
        print("   Get a free API key at: https://openrouter.ai/keys")

        if sys.stdin.isatty():
            api_choice = input("\nEnter OpenRouter API key (or press Enter to skip): ").strip()
        else:
            api_choice = os.environ.get("OPENROUTER_API_KEY", "").strip()

        if api_choice:
            # Validate API key
            from jarvis_bud.ai import OpenRouterClient

            print("\n🔍 Validating OpenRouter key...")
            client = OpenRouterClient(api_key=api_choice)

            if client.is_available:
                print("✅ OpenRouter API key is valid!\n")
                self.config["openrouter"] = {"api_key": api_choice, "model": client.model}
            else:
                print("❌ API key validation failed. Skipping OpenRouter.\n")
                self.config["openrouter"] = None
        else:
            print("\nℹ️  OpenRouter skipped. Using local Ollama or fallback.\n")
            self.config["openrouter"] = None

        if sys.stdin.isatty():
            print("🗣️  Voice stack options")
            stt_model = input("   STT model (default tiny.en): ").strip() or "tiny.en"
            tts_profile = (
                input("   TTS profile [cyberpunk/calm/standard] (default cyberpunk): ")
                .strip()
                .lower()
                or "cyberpunk"
            )
            if tts_profile not in {"cyberpunk", "calm", "standard"}:
                tts_profile = "cyberpunk"
            tts_model_path = input(
                "   Piper model path (default models/piper/en_US-lessac-medium.onnx): "
            ).strip()
        else:
            stt_model = os.environ.get("NXTGENAI_STT_MODEL", "tiny.en").strip() or "tiny.en"
            tts_profile = (
                os.environ.get("NXTGENAI_TTS_PROFILE", "cyberpunk").strip().lower() or "cyberpunk"
            )
            if tts_profile not in {"cyberpunk", "calm", "standard"}:
                tts_profile = "cyberpunk"
            tts_model_path = os.environ.get("NXTGENAI_TTS_MODEL", "").strip()

        self.config["stt"] = {
            "engine": "faster-whisper",
            "model_size": stt_model,
            "sample_rate": 16000,
        }
        self.config["tts"] = {
            "engine": "piper",
            "profile": tts_profile,
            "model_path": tts_model_path or "models/piper/en_US-lessac-medium.onnx",
        }
        self.config["ai"] = {
            "prefer_local_first": True,
            "offline_fallback_model": "models/tinyllama-1.1b-chat-v1.0-Q4_K_M.gguf",
        }
        self.config["dashboard"] = {"enabled": True, "host": "127.0.0.1", "port": 8080}
        self.config["ota"] = {"enabled": True, "remote": "origin"}
        self.config["sync"] = {
            "enabled": False,
            "port": 8091,
            "service_type": "_omnibot._tcp.local.",
        }
        return True

    def _save_config(self) -> bool:
        """Save configuration to config.json."""
        try:
            # Ensure config directory exists
            os.makedirs(os.path.dirname(self.config_path) or ".", exist_ok=True)

            with open(self.config_path, "w") as f:
                json.dump(self.config, f, indent=2)

            print(f"💾 Configuration saved to {self.config_path}")
            return True

        except Exception as e:
            print(f"❌ Failed to save config: {e}")
            return False

    def load_config(self) -> dict | None:
        """Load existing configuration.

        Returns:
            Config dict or None if not found
        """
        try:
            with open(self.config_path) as f:
                return json.load(f)
        except Exception:
            return None
