"""Frame Renderer for Jarvis-Bud LCD Display."""

from typing import Optional, Dict, Any
from .themes import TerminalDarkTheme, Color
from .animations import AnimationFrame


class FrameRenderer:
    """Renders complete UI frames to the display."""
    
    def __init__(self, display_width=240, display_height=280):
        """Initialize frame renderer.
        
        Args:
            display_width: Display width in pixels
            display_height: Display height in pixels
        """
        self.width = display_width
        self.height = display_height
        self.theme = TerminalDarkTheme()

    def render_status_hud(
        self,
        lcd_display,
        bud_name: str,
        battery_level: int,
        is_charging: bool,
        connectivity_status: str,
        animation_frame: Optional[AnimationFrame] = None,
        activity_icon: str = ""
    ) -> bool:
        """Render the main status HUD.
        
        Args:
            lcd_display: ST7789Display object
            bud_name: Name of current personality
            battery_level: Battery percentage (0-100)
            is_charging: Whether device is charging
            connectivity_status: Connection status ("offline", "local", "cloud")
            animation_frame: Optional animation frame for waveform
            
        Returns:
            True if successful
        """
        try:
            # Clear screen
            lcd_display.clear(self.theme.BACKGROUND.rgb())
            
            # Top bar: Status icons
            self._render_top_bar(
                lcd_display,
                battery_level,
                is_charging,
                connectivity_status,
                activity_icon,
            )
            
            # Title: Current Bud name
            bud_color = self.theme.get_personality_color(bud_name.split()[0].lower())
            lcd_display.draw_text(
                120,
                40,
                f"📍 {bud_name}",
                color=bud_color.rgb(),
                font="lg",
                center=True
            )
            
            # Waveform animation area
            if animation_frame:
                self._render_waveform(lcd_display, animation_frame)
            
            # Bottom info
            self._render_bottom_info(lcd_display, connectivity_status)
            
            # Update display
            lcd_display.update()
            return True
            
        except Exception as e:
            print(f"❌ Failed to render status HUD: {e}")
            return False

    def render_wizard_step(
        self,
        lcd_display,
        step_number: int,
        step_title: str,
        content_lines: list,
        progress: float = 0.0
    ) -> bool:
        """Render a wizard setup step.
        
        Args:
            lcd_display: ST7789Display object
            step_number: Step number (1-4)
            step_title: Title of current step
            content_lines: Lines of text to display
            progress: Setup progress (0.0-1.0)
            
        Returns:
            True if successful
        """
        try:
            lcd_display.clear(self.theme.BACKGROUND.rgb())
            
            # Progress bar at top
            self._render_progress_bar(lcd_display, progress)
            
            # Step header
            header_text = f"Step {step_number}/4: {step_title}"
            lcd_display.draw_text(
                120,
                30,
                header_text,
                color=self.theme.NEON_BLUE.rgb(),
                font="md",
                center=True
            )
            
            # Content lines
            y_pos = 80
            for line in content_lines:
                lcd_display.draw_text(
                    20,
                    y_pos,
                    line,
                    color=self.theme.TEXT_PRIMARY.rgb(),
                    font="sm"
                )
                y_pos += 30
            
            # Instructions at bottom
            lcd_display.draw_text(
                120,
                250,
                "Press Button A to continue",
                color=self.theme.TEXT_MUTED.rgb(),
                font="sm",
                center=True
            )
            
            lcd_display.update()
            return True
            
        except Exception as e:
            print(f"❌ Failed to render wizard step: {e}")
            return False

    def render_message(
        self,
        lcd_display,
        title: str,
        message: str,
        emoji: str = "💬",
        message_type: str = "info"
    ) -> bool:
        """Render a centered message on screen.
        
        Args:
            lcd_display: ST7789Display object
            title: Message title
            message: Message content
            emoji: Emoji to display
            message_type: Type ("info", "warning", "error", "success")
            
        Returns:
            True if successful
        """
        try:
            type_colors = {
                "info": self.theme.INFO,
                "warning": self.theme.WARNING,
                "error": self.theme.ERROR,
                "success": self.theme.SUCCESS,
            }
            color = type_colors.get(message_type, self.theme.INFO)
            
            lcd_display.clear(self.theme.BACKGROUND.rgb())
            
            # Emoji
            lcd_display.draw_text(
                120,
                60,
                emoji,
                color=color.rgb(),
                font="lg",
                center=True
            )
            
            # Title
            lcd_display.draw_text(
                120,
                120,
                title,
                color=color.rgb(),
                font="md",
                center=True
            )
            
            # Message (wrapped)
            lcd_display.draw_text(
                120,
                170,
                message,
                color=self.theme.TEXT_PRIMARY.rgb(),
                font="sm",
                center=True
            )
            
            lcd_display.update()
            return True
            
        except Exception as e:
            print(f"❌ Failed to render message: {e}")
            return False

    def _render_top_bar(
        self,
        lcd_display,
        battery_level: int,
        is_charging: bool,
        connectivity_status: str,
        activity_icon: str = ""
    ):
        """Render top status bar."""
        # Battery icon
        battery_text = f"🔌 {battery_level}%" if is_charging else f"🔋 {battery_level}%"
        lcd_display.draw_text(
            10,
            5,
            battery_text,
            color=self.theme.WARNING.rgb() if battery_level < 20 else self.theme.TEXT_SECONDARY.rgb(),
            font="sm"
        )
        
        # Connectivity icon
        connectivity_icons = {
            "offline": "📡",
            "local": "🏠",
            "cloud": "☁️"
        }
        icon = connectivity_icons.get(connectivity_status, "❓")
        lcd_display.draw_text(
            200,
            5,
            icon,
            color=self.theme.TEXT_SECONDARY.rgb(),
            font="sm"
        )

        if activity_icon:
            lcd_display.draw_text(
                110,
                5,
                activity_icon,
                color=self.theme.NEON_GREEN.rgb(),
                font="sm",
            )
        
        # Thin separator line
        lcd_display.draw_line(0, 20, self.width, 20, color=self.theme.NEON_BLUE.rgb(), width=1)

    def _render_waveform(self, lcd_display, animation_frame: AnimationFrame):
        """Render waveform animation."""
        try:
            lcd_display.draw_waveform(
                animation_frame.samples,
                x=20,
                y=100,
                height=100,
                color=self.theme.NEON_GREEN.rgb()
            )
        except Exception as e:
            print(f"⚠️  Error rendering waveform: {e}")

    def _render_bottom_info(self, lcd_display, connectivity_status: str):
        """Render bottom information area."""
        connectivity_text = {
            "offline": "Offline Mode",
            "local": "Local Ollama",
            "cloud": "OpenRouter Cloud"
        }
        text = connectivity_text.get(connectivity_status, "Unknown")
        
        lcd_display.draw_text(
            120,
            255,
            text,
            color=self.theme.TEXT_MUTED.rgb(),
            font="sm",
            center=True
        )

    def _render_progress_bar(self, lcd_display, progress: float):
        """Render a progress bar."""
        bar_width = int(self.width * progress)
        
        # Background
        lcd_display.draw_rectangle(
            0, 0, self.width, 3,
            color=self.theme.SURFACE.rgb(),
            fill=self.theme.SURFACE.rgb()
        )
        
        # Progress
        lcd_display.draw_rectangle(
            0, 0, bar_width, 3,
            color=self.theme.NEON_CYAN.rgb(),
            fill=self.theme.NEON_CYAN.rgb()
        )
