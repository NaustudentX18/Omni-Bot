"""First-Boot Setup Wizard for Jarvis-Bud."""

import json
import os
import time
from typing import Optional, Dict, Any
from pathlib import Path


class SetupWizard:
    """
    Interactive 4-step setup wizard for first-boot configuration.
    Guides user through hardware check, connectivity, personality selection, and API setup.
    """

    STEPS = {
        1: "Hardware Check 🔧",
        2: "Connectivity 📡",
        3: "Pick Your Bud 🤝",
        4: "API Configuration 🔑"
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
        
        self._load_buds()

    def _load_buds(self):
        """Load available Buds from buds.json."""
        try:
            with open(self.buds_path, 'r') as f:
                data = json.load(f)
                self.buds = {bud["id"]: bud for bud in data.get("buds", [])}
                print(f"✅ Loaded {len(self.buds)} personalities from buds.json")
        except Exception as e:
            print(f"⚠️  Could not load buds: {e}")
            self.buds = {}

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
                print(f"   ✅ Battery: {status['percentage']:.0f}% {status.get('charging') and '(Charging)' or ''}")
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

    def _step_2_connectivity(self) -> bool:
        """Step 2: Connectivity Check.
        
        Tests WiFi and Pironman server connectivity.
        """
        print(f"\n{'Step 2: Connectivity 📡':^60}")
        print("-" * 60)
        
        connectivity = {}
        
        # WiFi Check
        print("\n📳 Scanning WiFi networks...")
        try:
            import subprocess
            result = subprocess.run(
                ["iwlist", "wlan0", "scanning"],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                print("   ✅ WiFi scan successful")
                connectivity["wifi"] = "✅"
            else:
                print("   ⚠️  WiFi scan returned no output")
                connectivity["wifi"] = "⚠️"
        except Exception as e:
            print(f"   ⚠️  WiFi check disabled: {e}")
            connectivity["wifi"] = "⚠️"
        
        # Pironman/Ollama Check
        print("\n🌐 Checking for local Ollama server...")
        try:
            from jarvis_bud.ai import OllamaClient
            
            for url in ["http://localhost:11434", "http://192.168.1.100:11434", "http://naspi:11434", "http://pironman:11434"]:
                client = OllamaClient(base_url=url)
                if client.is_available:
                    print(f"   ✅ Local Ollama found at {url}")
                    connectivity["ollama"] = url
                    break
            
            if "ollama" not in connectivity:
                print("   ℹ️  No local Ollama found (that's OK, can use cloud)")
                connectivity["ollama"] = None
                
        except Exception as e:
            print(f"   ℹ️  Ollama check skipped: {e}")
            connectivity["ollama"] = None
        
        self.config["connectivity"] = connectivity
        return True

    def _step_3_personality_selection(self) -> bool:
        """Step 3: Select Personality/Bud.
        
        User chooses from available personalities.
        """
        print(f"\n{'Step 3: Pick Your Bud 🤝':^60}")
        print("-" * 60)
        print("\nAvailable personalities:\n")
        
        bud_list = list(self.buds.values())
        
        for i, bud in enumerate(bud_list, 1):
            print(f"  {i}. {bud['name']}")
            print(f"     └─ {bud['description']}\n")
        
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

    def _step_4_api_configuration(self) -> bool:
        """Step 4: API Configuration.
        
        User enters OpenRouter key or confirms Ollama.
        """
        print(f"\n{'Step 4: API Configuration 🔑':^60}")
        print("-" * 60)
        
        print("\n🌐 OpenRouter Setup (Optional but recommended for mobile use)")
        print("   Get a free API key at: https://openrouter.ai/keys")
        
        api_choice = input("\nEnter OpenRouter API key (or press Enter to skip): ").strip()
        
        if api_choice:
            # Validate API key
            from jarvis_bud.ai import OpenRouterClient
            
            print("\n🔍 Validating OpenRouter key...")
            client = OpenRouterClient(api_key=api_choice)
            
            if client.is_available:
                print("✅ OpenRouter API key is valid!\n")
                self.config["openrouter"] = {
                    "api_key": api_choice,
                    "model": client.model
                }
                return True
            else:
                print("❌ API key validation failed. Skipping OpenRouter.\n")
                self.config["openrouter"] = None
        else:
            print("\nℹ️  OpenRouter skipped. Using local Ollama or fallback.\n")
            self.config["openrouter"] = None
        
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
