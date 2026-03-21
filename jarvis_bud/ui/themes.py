"""Terminal-Dark theme with Neon accents for Jarvis-Bud."""

from dataclasses import dataclass


@dataclass
class Color:
    """Color definition with RGB values."""

    r: int
    g: int
    b: int

    def rgb(self) -> tuple[int, int, int]:
        """Get RGB tuple."""
        return (self.r, self.g, self.b)

    def hex(self) -> str:
        """Get hex color string."""
        return f"#{self.r:02x}{self.g:02x}{self.b:02x}"


class TerminalDarkTheme:
    """Terminal-Dark aesthetic theme with Neon accents."""

    # Base colors
    BACKGROUND = Color(10, 10, 15)  # Deep dark blue-black
    SURFACE = Color(20, 20, 30)  # Slightly lighter surface
    TEXT_PRIMARY = Color(210, 220, 230)  # Light gray
    TEXT_SECONDARY = Color(120, 130, 150)  # Medium gray
    TEXT_MUTED = Color(70, 80, 100)  # Dark gray

    # Neon accents
    NEON_GREEN = Color(0, 255, 100)  # Bright cyberpunk green
    NEON_BLUE = Color(0, 150, 255)  # Bright cyberpunk blue
    NEON_MAGENTA = Color(255, 0, 150)  # Hot magenta
    NEON_CYAN = Color(0, 255, 255)  # Cyan
    NEON_YELLOW = Color(255, 255, 0)  # Bright yellow

    # Status colors
    SUCCESS = NEON_GREEN
    WARNING = NEON_YELLOW
    ERROR = Color(255, 60, 60)  # Deep red
    INFO = NEON_CYAN

    # Personality accent overrides
    PERSONALITY_COLORS = {
        "fogo": NEON_GREEN,
        "mango": NEON_YELLOW,
        "tech-support": NEON_GREEN,
        "trail-runner": NEON_BLUE,
        "snarky-hacker": NEON_MAGENTA,
        "zen-guide": NEON_YELLOW,
    }

    @staticmethod
    def get_personality_color(personality_id: str):
        """Get neon accent color for a personality.

        Args:
            personality_id: Personality ID (e.g., "tech-support")

        Returns:
            Color object
        """
        return TerminalDarkTheme.PERSONALITY_COLORS.get(
            personality_id, TerminalDarkTheme.NEON_GREEN
        )

    @staticmethod
    def get_border_accent():
        """Get color for UI borders."""
        return TerminalDarkTheme.NEON_BLUE

    @staticmethod
    def get_text_with_emoji(text: str, emoji: str) -> str:
        """Format text with emoji for display.

        Args:
            text: Main text
            emoji: Emoji character

        Returns:
            Formatted string
        """
        return f"{emoji} {text}"
