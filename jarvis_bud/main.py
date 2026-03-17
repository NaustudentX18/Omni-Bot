"""Main Entry Point for Jarvis-Bud."""

import asyncio
import json
import sys
from typing import Optional

# Import all modules
from jarvis_bud.config import ConfigManager
from jarvis_bud.wizard import SetupWizard
from jarvis_bud.hardware import ST7789Display, AudioCodec, Battery, ButtonHandler
from jarvis_bud.ui import FrameRenderer, WaveformAnimator
from jarvis_bud.ai import AIRouter


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
        self.display: Optional[ST7789Display] = None
        self.audio: Optional[AudioCodec] = None
        self.battery: Optional[Battery] = None
        self.buttons: Optional[ButtonHandler] = None
        
        # UI
        self.renderer: Optional[FrameRenderer] = None
        self.animator = WaveformAnimator()
        
        # AI
        self.ai_router: Optional[AIRouter] = None
        
        # State
        self.is_listening = False
        self.is_running = True
        self.current_bud = None
        self.connectivity_mode = "offline"

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
            # Initialize Display
            self.display = ST7789Display()
            if not self.display.init():
                print("⚠️  Display initialization failed, continuing...")
            
            # Initialize Audio
            self.audio = AudioCodec()
            if not self.audio.init():
                print("⚠️  Audio initialization failed, continuing...")
            
            # Initialize Battery
            self.battery = Battery()
            self.battery.connect()
            
            # Initialize Buttons
            self.buttons = ButtonHandler()
            self.buttons.on_button_a(self._on_button_a_pressed)
            self.buttons.on_button_b(self._on_button_b_pressed)
            
            # Initialize UI Renderer
            self.renderer = FrameRenderer()
            
            print("✅ Hardware initialized successfully\n")
            return True
            
        except Exception as e:
            print(f"❌ Hardware initialization error: {e}")
            return False

    def initialize_ai(self) -> bool:
        """Initialize AI router with configured backends.
        
        Returns:
            True if at least one AI route available
        """
        print("\n🧠 Initializing AI router...\n")
        
        try:
            ollama_url = self.config_manager.get_ollama_url()
            openrouter_key = self.config_manager.get_openrouter_key()
            
            self.ai_router = AIRouter(
                ollama_url=ollama_url,
                openrouter_key=openrouter_key
            )
            
            route_info = self.ai_router.get_route_info()
            
            if route_info["local_available"]:
                print(f"✅ Local Ollama available: {route_info['local_model']}")
                self.connectivity_mode = "local"
            
            if route_info["cloud_available"]:
                print(f"✅ OpenRouter available: {route_info['cloud_model']}")
                self.connectivity_mode = "cloud"
            
            if not route_info["local_available"] and not route_info["cloud_available"]:
                print("⚠️  No AI routes available. Running in demo mode.")
                self.connectivity_mode = "offline"
            
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
        # This would cycle through available personalities
        # For now, just a placeholder
        print("💫 Cycle Buds feature coming soon!")

    async def _listen_and_respond(self):
        """Listen for audio input and generate AI response."""
        if not self.display or not self.audio:
            return
        
        try:
            # Show listening animation
            if self.renderer:
                animation_frame = self.animator.get_frame("listening")
                self.renderer.render_status_hud(
                    self.display,
                    bud_name=self.current_bud or "Jarvis-Bud",
                    battery_level=self.battery.get_battery_percentage() if self.battery else 100,
                    is_charging=self.battery.is_charging() if self.battery else False,
                    connectivity_status=self.connectivity_mode,
                    animation_frame=animation_frame
                )
            
            print("🎙️  Listening... (say something or press Button A to stop)")
            
            # Record audio for 5 seconds
            self.audio.start_recording()
            await asyncio.sleep(5)
            audio_data = self.audio.stop_recording()
            
            if not audio_data:
                print("❌ No audio captured")
                self.is_listening = False
                return
            
            # Show thinking animation
            if self.renderer:
                animation_frame = self.animator.get_frame("thinking")
                self.renderer.render_status_hud(
                    self.display,
                    bud_name=self.current_bud or "Jarvis-Bud",
                    battery_level=self.battery.get_battery_percentage() if self.battery else 100,
                    is_charging=self.battery.is_charging() if self.battery else False,
                    connectivity_status=self.connectivity_mode,
                    animation_frame=animation_frame
                )
            
            print("🤔 Thinking...")
            
            # Generate response using AI router
            if self.ai_router:
                system_prompt = self.config_manager.get_bud_system_prompt()
                user_prompt = "I recorded some audio, please generate a helpful response"
                
                response = self.ai_router.generate(
                    user_prompt,
                    system_prompt=system_prompt,
                    prefer="auto"
                )
                
                if response:
                    print(f"💬 Response: {response[:100]}...")
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
                if self.display and self.renderer:
                    # Get current state
                    battery_pct = self.battery.get_battery_percentage() if self.battery else 100
                    is_charging = self.battery.is_charging() if self.battery else False
                    
                    # Get animation frame based on state
                    if self.is_listening:
                        audio_level = self.audio.get_audio_level() if self.audio else 0.5
                        animation_frame = self.animator.get_frame("listening", audio_level=audio_level)
                    else:
                        animation_frame = self.animator.get_frame("idle")
                    
                    # Render HUD
                    self.renderer.render_status_hud(
                        self.display,
                        bud_name=self.current_bud or "Jarvis-Bud 🤖",
                        battery_level=battery_pct,
                        is_charging=is_charging,
                        connectivity_status=self.connectivity_mode,
                        animation_frame=animation_frame
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
                    status = self.battery.get_status()
                    
                    # Warn if battery is critical
                    if self.battery.is_low_battery(threshold=10):
                        print("🚨 CRITICAL: Battery very low!")
                        if self.renderer and self.display:
                            self.renderer.render_message(
                                self.display,
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
        
        if self.buttons:
            self.buttons.cleanup()
        
        if self.audio:
            self.audio.cleanup()
        
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
