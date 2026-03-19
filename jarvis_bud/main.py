"""Main Entry Point for Jarvis-Bud."""

import asyncio
import sys
import time
from typing import Optional

from jarvis_bud.config import ConfigManager
from jarvis_bud.wizard import SetupWizard
from jarvis_bud.hardware import Battery, WhisplayIO
from jarvis_bud.ui import FrameRenderer, WaveformAnimator
from jarvis_bud.core import BudManager, LocalOllamaClient


class JarvisBud:
    """Main Jarvis-Bud application controller."""

    def __init__(self, config_path: str = "config/config.json", buds_path: str = "jarvis_bud/buds.json"):
        """Initialize Jarvis-Bud.
        
        Args:
            config_path: Path to config.json
            buds_path: Path to buds.json
        """
        self.config_manager = ConfigManager(config_path)
        self.buds_path = buds_path
        
        # Hardware
        self.whisplay: Optional[WhisplayIO] = None
        self.battery: Optional[Battery] = None
        
        # UI
        self.renderer: Optional[FrameRenderer] = None
        self.animator = WaveformAnimator()
        
        # AI and personalities
        self.bud_manager: Optional[BudManager] = None
        
        # State
        self.is_listening = False
        self.is_running = True
        self.current_bud = "Fogo"
        self.connectivity_mode = "offline"
        self._last_prompt = ""
        self._battery_snapshot = {"percentage": 100, "charging": False}
        self._last_battery_refresh = 0.0
        self._battery_refresh_interval_s = 2.0

    def _refresh_battery_snapshot(self, force: bool = False) -> dict:
        """Refresh cached battery status with light rate limiting."""
        now = time.monotonic()
        should_refresh = force or (now - self._last_battery_refresh) >= self._battery_refresh_interval_s

        if should_refresh and self.battery:
            status = self.battery.get_status()
            self._battery_snapshot["percentage"] = int(status.get("percentage", 100))
            self._battery_snapshot["charging"] = bool(status.get("charging", False))
            self._last_battery_refresh = now

        return self._battery_snapshot

    def run_first_boot_if_needed(self) -> bool:
        """Run first-boot wizard if config doesn't exist.
        
        Returns:
            True if setup successful or already configured
        """
        if not self.config_manager.is_configured():
            print("\n🎯 First-time setup detected!\n")
            
            wizard = SetupWizard(
                config_path=self.config_manager.config_path,
                buds_path=self.buds_path
            )
            
            if wizard.run_interactive():
                # Reload config after wizard
                self.config_manager.load()
                return True
            else:
                print("\n❌ Setup wizard failed. Please try again.")
                return False
        
        return True

    def initialize_hardware(self) -> bool:
        """Initialize all hardware components.
        
        Returns:
            True if critical hardware initialized
        """
        print("\n🔧 Initializing hardware...\n")
        
        try:
            self.whisplay = WhisplayIO()
            if not self.whisplay.initialize():
                print("❌ Whisplay initialization failed")
                return False
            
            # Initialize Battery
            self.battery = Battery()
            self.battery.connect()
            
            # Initialize Buttons
            self.whisplay.set_callbacks(
                on_button_a=self._on_button_a_pressed,
                on_button_b=self._on_button_b_pressed,
            )
            
            # Initialize UI Renderer
            self.renderer = FrameRenderer()
            
            print("✅ Hardware initialized successfully\n")
            return True
            
        except Exception as e:
            print(f"❌ Hardware initialization error: {e}")
            return False

    def initialize_ai(self) -> bool:
        """Initialize local-first AI routing with OpenRouter failover."""
        print("\n🧠 Initializing Fogo routing stack...\n")

        try:
            configured_ollama = self.config_manager.get_ollama_url()
            candidates = ["127.0.0.1", "pironman", "naspi", "192.168.1.100", "192.168.1.101", "192.168.1.110"]
            if configured_ollama and configured_ollama.startswith("http://"):
                host = configured_ollama.replace("http://", "").split(":")[0]
                if host not in candidates:
                    candidates.insert(0, host)

            ollama = LocalOllamaClient(candidate_hosts=candidates, max_ping_ms=100.0)
            endpoint = ollama.scan()

            self.bud_manager = BudManager(
                ollama=ollama,
                openrouter_key=self.config_manager.get_openrouter_key(),
            )

            preferred = self.config_manager.get("bud.id", "fogo")
            self.bud_manager.set_active_bud(preferred if preferred in self.bud_manager.buds else "fogo")
            self.current_bud = self.bud_manager.active_profile.name

            if endpoint:
                self.connectivity_mode = "local"
                print(f"✅ Ollama endpoint: {endpoint.base_url} ({endpoint.latency_ms:.1f}ms)")
                print(f"✅ Active local model: {ollama.model or 'llama3/mistral'}")
            elif self.bud_manager.openrouter and self.bud_manager.openrouter.is_available:
                self.connectivity_mode = "cloud"
                print("✅ Local offline, using OpenRouter failover")
            else:
                self.connectivity_mode = "offline"
                print("⚠️ No available AI route right now")

            print()
            return True

        except Exception as e:
            print(f"❌ AI initialization error: {e}")
            self.connectivity_mode = "offline"
            return False

    def _on_button_a_pressed(self):
        """Handle Button A press (Listen/Wake)."""
        print("🔘 Button A pressed (Listen)")
        
        if not self.is_listening:
            self.is_listening = True
            asyncio.create_task(self._listen_and_respond())

    def _on_button_b_pressed(self):
        """Handle Button B press (Cycle Personalities)."""
        print("🔘 Button B pressed (Cycle Bud)")
        if not self.bud_manager:
            return
        profile = self.bud_manager.cycle_bud()
        self.current_bud = profile.name
        self.config_manager.set("bud.id", profile.bud_id)
        self.config_manager.set("bud.name", profile.name)
        self.config_manager.set("bud.system_prompt", profile.system_prompt)
        self.config_manager.save()
        print(f"💫 Active Bud: {profile.name} {profile.emoji}")

    async def _listen_and_respond(self):
        """Listen for audio input and generate AI response."""
        if not self.whisplay:
            return
        
        try:
            # Show listening animation
            if self.renderer:
                battery_snapshot = self._refresh_battery_snapshot(force=True)
                animation_frame = self.animator.get_frame("listening")
                self.renderer.render_status_hud(
                    self.whisplay.display,
                    bud_name=self.current_bud or "Jarvis-Bud",
                    battery_level=battery_snapshot["percentage"],
                    is_charging=battery_snapshot["charging"],
                    connectivity_status=self.connectivity_mode,
                    animation_frame=animation_frame,
                    activity_icon=self.bud_manager.active_icon(self._last_prompt) if self.bud_manager else "",
                )
            
            print("🎙️  Listening... (say something or press Button A to stop)")
            
            # Record audio for 4 seconds
            audio_data = await self.whisplay.capture_audio(seconds=4.0)
            
            if not audio_data:
                print("❌ No audio captured")
                self.is_listening = False
                return
            
            # Show thinking animation
            if self.renderer:
                battery_snapshot = self._refresh_battery_snapshot()
                animation_frame = self.animator.get_frame("thinking")
                self.renderer.render_status_hud(
                    self.whisplay.display,
                    bud_name=self.current_bud or "Jarvis-Bud",
                    battery_level=battery_snapshot["percentage"],
                    is_charging=battery_snapshot["charging"],
                    connectivity_status=self.connectivity_mode,
                    animation_frame=animation_frame,
                    activity_icon=self.bud_manager.active_icon(self._last_prompt) if self.bud_manager else "",
                )
            
            print("🤔 Thinking...")
            
            # Generate response using Bud manager
            if self.bud_manager:
                self._last_prompt = "I recorded some audio, please generate a helpful response"
                response = self.bud_manager.generate_response(self._last_prompt)

                local_online = self.bud_manager.ollama.is_available
                cloud_online = bool(self.bud_manager.openrouter and self.bud_manager.openrouter.is_available)
                if local_online:
                    self.connectivity_mode = "local"
                elif cloud_online:
                    self.connectivity_mode = "cloud"
                else:
                    self.connectivity_mode = "offline"

                if response:
                    print(f"💬 Response: {response[:140]}...")
                else:
                    print("❌ No response generated")
            
            self.is_listening = False
            
        except Exception as e:
            print(f"❌ Error in listen_and_respond: {e}")
            self.is_listening = False

    async def _update_display_loop(self):
        """Main display update loop (60fps)."""
        frame_interval = 1.0 / 60  # 60 FPS
        
        while self.is_running:
            try:
                if self.whisplay and self.renderer:
                    # Get current state
                    battery_snapshot = self._refresh_battery_snapshot()
                    
                    # Get animation frame based on state
                    if self.is_listening:
                        audio_level = self.whisplay.audio.get_audio_level() if self.whisplay else 0.5
                        animation_frame = self.animator.get_frame("listening", audio_level=audio_level)
                    else:
                        animation_frame = self.animator.get_frame("idle")
                    
                    # Render HUD
                    self.renderer.render_status_hud(
                        self.whisplay.display,
                        bud_name=self.current_bud or "Jarvis-Bud 🤖",
                        battery_level=battery_snapshot["percentage"],
                        is_charging=battery_snapshot["charging"],
                        connectivity_status=self.connectivity_mode,
                        animation_frame=animation_frame,
                        activity_icon=self.bud_manager.active_icon(self._last_prompt) if self.bud_manager else "",
                    )
                
                await asyncio.sleep(frame_interval)
                
            except Exception as e:
                print(f"⚠️  Display update error: {e}")
                await asyncio.sleep(frame_interval)

    async def _battery_monitor_loop(self):
        """Monitor battery in background."""
        while self.is_running:
            try:
                if self.battery:
                    status = self._refresh_battery_snapshot(force=True)
                    
                    # Warn if battery is critical
                    if status["percentage"] < 10:
                        print("🚨 CRITICAL: Battery very low!")
                        if self.renderer and self.whisplay:
                            self.renderer.render_message(
                                self.whisplay.display,
                                "Battery Critical",
                                "Shutting down soon...",
                                emoji="🪫",
                                message_type="error"
                            )
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                print(f"⚠️  Battery monitor error: {e}")
                await asyncio.sleep(10)

    async def async_main_loop(self):
        """Main async event loop.
        
        Runs display updates, button monitoring, and AI tasks concurrently.
        """
        print("\n🚀 Starting Jarvis-Bud async event loop...\n")
        
        tasks = [
            asyncio.create_task(self._update_display_loop()),
            asyncio.create_task(self._battery_monitor_loop()),
        ]
        
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            print("\n\n⏹️  Shutting down...")
            self.is_running = False
            
            # Wait for tasks to complete
            for task in tasks:
                task.cancel()
            
            await asyncio.gather(*tasks, return_exceptions=True)

    def cleanup(self):
        """Clean up resources."""
        print("\n🧹 Cleaning up...\n")
        
        if self.whisplay:
            self.whisplay.cleanup()
        
        if self.battery:
            self.battery.disconnect()
        
        print("✅ Cleanup complete\n")

    def run(self):
        """Run the complete Jarvis-Bud application."""
        try:
            # First-boot wizard
            if not self.run_first_boot_if_needed():
                return False
            
            # Load configuration
            self.config_manager.print_config()
            self.current_bud = self.config_manager.get("bud.name", "Jarvis-Bud")
            
            # Initialize hardware
            if not self.initialize_hardware():
                print("❌ Critical hardware initialization failed")
                return False
            
            # Initialize AI
            self.initialize_ai()
            
            # Run main event loop
            asyncio.run(self.async_main_loop())
            
            return True
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            return True
        except Exception as e:
            print(f"\n❌ Fatal error: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            self.cleanup()


def main():
    """Entry point."""
    app = JarvisBud()
    success = app.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
