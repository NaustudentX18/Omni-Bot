"""Frame Renderer for Jarvis-Bud LCD Display."""

import random

from .animations import AnimationFrame
from .themes import TerminalDarkTheme


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
        animation_frame: AnimationFrame | None = None,
        activity_icon: str = "",
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
                120, 40, f"📍 {bud_name}", color=bud_color.rgb(), font="lg", center=True
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
        progress: float = 0.0,
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
                120, 30, header_text, color=self.theme.NEON_BLUE.rgb(), font="md", center=True
            )

            # Content lines
            y_pos = 80
            for line in content_lines:
                lcd_display.draw_text(
                    20, y_pos, line, color=self.theme.TEXT_PRIMARY.rgb(), font="sm"
                )
                y_pos += 30

            # Instructions at bottom
            lcd_display.draw_text(
                120,
                250,
                "Press Button A to continue",
                color=self.theme.TEXT_MUTED.rgb(),
                font="sm",
                center=True,
            )

            lcd_display.update()
            return True

        except Exception as e:
            print(f"❌ Failed to render wizard step: {e}")
            return False

    def render_message(
        self, lcd_display, title: str, message: str, emoji: str = "💬", message_type: str = "info"
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
            lcd_display.draw_text(120, 60, emoji, color=color.rgb(), font="lg", center=True)

            # Title
            lcd_display.draw_text(120, 120, title, color=color.rgb(), font="md", center=True)

            # Message (wrapped)
            lcd_display.draw_text(
                120, 170, message, color=self.theme.TEXT_PRIMARY.rgb(), font="sm", center=True
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
        activity_icon: str = "",
    ):
        """Render top status bar."""
        # Battery icon
        battery_text = f"🔌 {battery_level}%" if is_charging else f"🔋 {battery_level}%"
        lcd_display.draw_text(
            10,
            5,
            battery_text,
            color=(
                self.theme.WARNING.rgb() if battery_level < 20 else self.theme.TEXT_SECONDARY.rgb()
            ),
            font="sm",
        )

        # Connectivity icon
        connectivity_icons = {"offline": "📡", "local": "🏠", "cloud": "☁️"}
        icon = connectivity_icons.get(connectivity_status, "❓")
        lcd_display.draw_text(200, 5, icon, color=self.theme.TEXT_SECONDARY.rgb(), font="sm")

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
                animation_frame.samples, x=20, y=100, height=100, color=self.theme.NEON_GREEN.rgb()
            )
        except Exception as e:
            print(f"⚠️  Error rendering waveform: {e}")

    def _render_bottom_info(self, lcd_display, connectivity_status: str):
        """Render bottom information area."""
        connectivity_text = {
            "offline": "Offline Mode",
            "local": "Local Ollama",
            "cloud": "OpenRouter Cloud",
        }
        text = connectivity_text.get(connectivity_status, "Unknown")

        lcd_display.draw_text(
            120, 255, text, color=self.theme.TEXT_MUTED.rgb(), font="sm", center=True
        )

    def _render_progress_bar(self, lcd_display, progress: float):
        """Render a progress bar."""
        bar_width = int(self.width * progress)

        # Background
        lcd_display.draw_rectangle(
            0, 0, self.width, 3, color=self.theme.SURFACE.rgb(), fill=self.theme.SURFACE.rgb()
        )

        # Progress
        lcd_display.draw_rectangle(
            0, 0, bar_width, 3, color=self.theme.NEON_CYAN.rgb(), fill=self.theme.NEON_CYAN.rgb()
        )

    def render_matrix_boot(self, lcd_display, frame_idx: int, total_frames: int = 36) -> bool:
        """Render cyberpunk matrix-rain boot animation frame."""
        try:
            lcd_display.clear(self.theme.BACKGROUND.rgb())
            columns = 20
            col_width = max(8, self.width // columns)
            phase = frame_idx / max(1, total_frames)
            for col in range(columns):
                x = col * col_width + 2
                tail = int((phase * self.height + (col * 11) % self.height) % self.height)
                for offset in range(0, 60, 10):
                    y = tail - offset
                    if y < 0:
                        continue
                    glow = max(30, 255 - offset * 4)
                    color = (0, glow, min(180, glow))
                    lcd_display.draw_text(x, y, random.choice("01#@$"), color=color, font="sm")
            self.render_progress_overlay(
                lcd_display=lcd_display,
                progress=min(1.0, phase),
                label="BOOTING NXTGENAI",
            )
            lcd_display.update()
            return True
        except Exception as exc:
            print(f"⚠️  Matrix boot render failure: {exc}")
            return False

    def render_ai_thought_ticker(self, lcd_display, thought: str, offset: int = 0) -> None:
        """Render scrolling 'AI thought' ticker for live model introspection."""
        ticker = f"AI THOUGHT // {thought or 'idle-scan'} // "
        padded = ticker * 3
        start = offset % len(ticker)
        segment = padded[start : start + 34]
        lcd_display.draw_rectangle(
            4, 220, self.width - 4, 244, color=self.theme.NEON_BLUE.rgb(), fill=(18, 18, 28)
        )
        lcd_display.draw_text(8, 224, segment, color=self.theme.NEON_CYAN.rgb(), font="sm")

    def render_risk_meter(self, lcd_display, risk: int, dry_run: bool = True) -> None:
        """Render neon risk meter for action gating."""
        risk = max(0, min(10, int(risk)))
        bar_left = 12
        bar_top = 248
        bar_w = self.width - 24
        fill_w = int((risk / 10.0) * bar_w)
        if risk >= 8:
            color = self.theme.ERROR.rgb()
        elif risk >= 6:
            color = self.theme.WARNING.rgb()
        else:
            color = self.theme.NEON_GREEN.rgb()
        lcd_display.draw_rectangle(
            bar_left,
            bar_top,
            bar_left + bar_w,
            bar_top + 12,
            color=self.theme.SURFACE.rgb(),
            fill=(22, 22, 34),
        )
        lcd_display.draw_rectangle(
            bar_left, bar_top, bar_left + fill_w, bar_top + 12, color=color, fill=color
        )
        mode = "DRY-RUN" if dry_run else "LIVE"
        lcd_display.draw_text(16, bar_top - 14, f"RISK {risk}/10 [{mode}]", color=color, font="sm")

    def render_progress_overlay(
        self, lcd_display, progress: float, label: str = "Processing"
    ) -> None:
        """Render a thick neon progress bar with label."""
        progress = max(0.0, min(1.0, progress))
        x1, y1 = 10, 256
        x2, y2 = self.width - 10, 272
        lcd_display.draw_rectangle(
            x1, y1, x2, y2, color=self.theme.SURFACE.rgb(), fill=(20, 20, 28)
        )
        fill = int((x2 - x1) * progress)
        lcd_display.draw_rectangle(
            x1,
            y1,
            x1 + fill,
            y2,
            color=self.theme.NEON_MAGENTA.rgb(),
            fill=self.theme.NEON_MAGENTA.rgb(),
        )
        lcd_display.draw_text(
            12,
            y1 - 16,
            f"{label}: {int(progress * 100)}%",
            color=self.theme.NEON_CYAN.rgb(),
            font="sm",
        )

    def apply_glitch(self, lcd_display, intensity: float = 0.2) -> None:
        """Overlay subtle glitch lines for cinematic mode."""
        lines = max(1, int(12 * max(0.0, min(1.0, intensity))))
        for _ in range(lines):
            y = random.randint(30, self.height - 24)
            x1 = random.randint(0, self.width // 3)
            x2 = min(self.width, x1 + random.randint(self.width // 3, self.width - 1))
            color = random.choice(
                [
                    self.theme.NEON_BLUE.rgb(),
                    self.theme.NEON_MAGENTA.rgb(),
                    self.theme.NEON_CYAN.rgb(),
                ]
            )
            lcd_display.draw_line(x1, y, x2, y, color=color, width=1)

    def render_idle_matrix_overlay(self, lcd_display, tick: int = 0) -> None:
        """Low-intensity matrix rain overlay for idle scenes."""
        for col in range(0, self.width, 16):
            y = (tick * 6 + col * 3) % max(1, self.height - 40)
            lcd_display.draw_text(col, y, random.choice("01"), color=(0, 120, 90), font="sm")
