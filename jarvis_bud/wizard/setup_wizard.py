"""First-Boot Setup Wizard for Jarvis-Bud."""

import json
import os
import time
from typing import Optional, Dict, Any
from pathlib import Path
import sys

from jarvis_bud.core import LocalOllamaClient
from jarvis_bud.ui import FrameRenderer
from jarvis_bud.hardware import ST7789Display


class SetupWizard:
    """
    Interactive 4-step setup wizard for first-boot configuration.
    Guides user through hardware check, connectivity, personality selection, and API setup.
    """

    STEPS = {
        1: "Hardware Check 🔧",
        2: "Network & API 📡🔑",
        3: "Pick Your Bud 🤝",
        4: "Final Review ✅",
    }

    def __init__(self, config_path: str = "config/config.json", buds_path: str = "jarvis_bud/buds.json"):
        """Initialize setup wizard.
        
        Args:
            config_path: Path to save config
            buds_path: Path to buds.json
        """
        self.config_path = config_path
        self.buds_path = buds_path
        self.config: Dict[str, Any] = {}
        self.buds: Dict[str, Any] = {}
        self.display: Optional[ST7789Display] = None
        self.renderer: Optional[FrameRenderer] = None
        
        self._load_buds()

    def _load_buds(self):
        """Load available Buds from buds.json."""
        try:
            with open(self.buds_path, 'r') as f:
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

    def _render_lcd_step(self, step_number: int, step_title: str, content_lines: list, progress: float):
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
        print("\n" + "="*60)
        print("🤖 JARVIS-BUD FIRST-BOOT WIZARD 🤖".center(60))
        print("="*60 + "\n")
        self._init_lcd()
        self._meet_fogo_splash()
        
        try:
            # Step 1: Hardware Check
            if not self._step_1_hardware_check():
                print("❌ Hardware check failed. Aborting setup.")
                return False

            # Step 2: Network & API (WiFi SSID/pass, OpenRouter key, device name)
            if not self._step_2_network_and_api():
                print("⚠️  Network config incomplete, but continuing...")

            # Step 3: Personality Selection
            if not self._step_3_personality_selection():
                print("❌ Personality selection failed. Aborting setup.")
                return False

            # Step 4: Final Review
            self._step_4_final_review()

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
        self._render_lcd_step(1, "Hardware Check", ["Testing LCD", "Testing WM8960", "Testing PiSugar 3"], 0.25)
        
        from jarvis_bud.hardware import ST7789Display, AudioCodec, Battery, ButtonHandler
        
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
                print(f"   ✅ Buttons initialized (A={buttons.button_a_gpio}, B={buttons.button_b_gpio})")
            else:
                results["buttons"] = "⚠️"
                print("   ⚠️  Buttons in mock mode")
        except Exception as e:
            results["buttons"] = "❌"
            print(f"   ❌ Buttons error: {e}")
        
        self.config["hardware"] = results
        
        # Check if at least LCD and Audio work
        return results.get("lcd") in ["✅", "⚠️"] and results.get("audio") in ["✅", "⚠️"]

    def _step_2_network_and_api(self) -> bool:
        """Step 2: Collect WiFi SSID/password, OpenRouter API key, device name, and scan LAN."""
        print(f"\n{'Step 2: Network & API 📡🔑':^60}")
        print("-" * 60)
        self._render_lcd_step(2, "Network & API", ["WiFi + API key", "Ollama scan", "Device name"], 0.5)

        network = {}

        # WiFi credentials
        print("\n📶 WiFi Configuration (saved for reconnection)")
        if sys.stdin.isatty():
            wifi_ssid = input("   WiFi SSID (or Enter to skip): ").strip()
            wifi_pass = input("   WiFi Password (or Enter to skip): ").strip() if wifi_ssid else ""
        else:
            wifi_ssid = os.environ.get("NXTGENAI_WIFI_SSID", "").strip()
            wifi_pass = os.environ.get("NXTGENAI_WIFI_PASS", "").strip()

        if wifi_ssid:
            network["wifi_ssid"] = wifi_ssid
            network["wifi_password"] = wifi_pass
            print(f"   ✅ WiFi SSID: {wifi_ssid}")
        else:
            print("   ℹ️  WiFi config skipped")

        # Device name
        print("\n🏷️  Device Name (for multi-device sync)")
        if sys.stdin.isatty():
            device_name = input("   Device name (default: nxtgenai-pi): ").strip()
        else:
            device_name = os.environ.get("NXTGENAI_DEVICE_NAME", "").strip()
        network["device_name"] = device_name or "nxtgenai-pi"
        print(f"   ✅ Device: {network['device_name']}")

        # OpenRouter API key
        print("\n🔑 OpenRouter API Key (free at https://openrouter.ai/keys)")
        if sys.stdin.isatty():
            api_key = input("   API key (or Enter to skip): ").strip()
        else:
            api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()

        if api_key:
            from jarvis_bud.ai import OpenRouterClient
            print("   🔍 Validating...")
            client = OpenRouterClient(api_key=api_key)
            if client.is_available:
                print("   ✅ OpenRouter key valid!")
                self.config["openrouter"] = {"api_key": api_key, "model": client.model}
            else:
                print("   ❌ Validation failed. Skipping OpenRouter.")
                self.config["openrouter"] = None
        else:
            print("   ℹ️  OpenRouter skipped. Offline brain + local Ollama only.")
            self.config["openrouter"] = None

        # LAN Ollama scan
        print("\n🌐 Scanning LAN for Ollama server...")
        try:
            candidates = ["192.168.1.100", "192.168.1.101", "192.168.1.110", "pironman", "naspi", "127.0.0.1"]
            scanner = LocalOllamaClient(candidate_hosts=candidates, max_ping_ms=100.0)
            endpoint = scanner.scan()
            if endpoint:
                url = endpoint.base_url
                print(f"   ✅ Ollama found: {url} ({endpoint.latency_ms:.1f}ms)")
                network["ollama"] = url
                network["ollama_latency_ms"] = endpoint.latency_ms
            else:
                print("   ℹ️  No Ollama found. Will use offline brain fallback.")
                network["ollama"] = None
        except Exception as e:
            print(f"   ℹ️  Ollama scan skipped: {e}")
            network["ollama"] = None

        self.config["connectivity"] = network
        return True

    def _step_3_personality_selection(self) -> bool:
        """Step 3: Select Personality/Bud.
        
        User chooses from available personalities.
        """
        print(f"\n{'Step 3: Pick Your Bud 🤝':^60}")
        print("-" * 60)
        print("\nAvailable personalities:\n")
        self._render_lcd_step(3, "Pick Your Bud", ["Fogo: maker brain", "Mango: chill vibe", "Button B cycles later"], 0.75)
        
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
                        "ui_accent_color": selected_bud["ui_accent_color"]
                    }
                    return True
                else:
                    print(f"❌ Please enter a number between 1 and {len(bud_list)}")
            except ValueError:
                print("❌ Invalid input. Please enter a number.")

    def _step_4_final_review(self) -> bool:
        """Step 4: Final Review - show summary of all configuration."""
        print(f"\n{'Step 4: Final Review ✅':^60}")
        print("-" * 60)
        self._render_lcd_step(4, "Final Review", ["Config ready", "Saving...", "Boot!"], 1.0)

        print("\n📋 Configuration Summary:\n")
        bud_cfg = self.config.get("bud", {})
        net_cfg = self.config.get("connectivity", {})
        or_cfg = self.config.get("openrouter")

        print(f"   🤖 Personality: {bud_cfg.get('name', 'Unknown')}")
        print(f"   📶 WiFi SSID:   {net_cfg.get('wifi_ssid', 'Not configured')}")
        print(f"   🏷️  Device:      {net_cfg.get('device_name', 'nxtgenai-pi')}")
        print(f"   🌐 Ollama:      {net_cfg.get('ollama') or 'Not found'}")
        print(f"   ☁️  OpenRouter:  {'Configured' if or_cfg else 'Skipped'}")
        print(f"   🧠 Offline AI:  EdgeBrain (GGUF fallback always available)")
        print(f"   🎙️  STT:        faster-whisper tiny (offline)")
        print(f"   🔊 TTS:        Piper -> espeak-ng -> silent")
        print()
        return True

    def _save_config(self) -> bool:
        """Save configuration to config.json."""
        try:
            # Ensure config directory exists
            os.makedirs(os.path.dirname(self.config_path) or ".", exist_ok=True)
            
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            
            print(f"💾 Configuration saved to {self.config_path}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to save config: {e}")
            return False

    def load_config(self) -> Optional[Dict]:
        """Load existing configuration.
        
        Returns:
            Config dict or None if not found
        """
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except Exception:
            return None
