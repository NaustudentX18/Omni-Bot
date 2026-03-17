"""ST7789 LCD Display Driver (240x280) for Jarvis-Bud."""

import os
from PIL import Image, ImageDraw, ImageFont


class ST7789Display:
    """
    ST7789 SPI LCD display controller for 240x280 resolution.
    Uses PIL for rendering, optimized for Raspberry Pi.
    """

    def __init__(self, width=240, height=280):
        """Initialize ST7789 display.
        
        Args:
            width: Display width (default 240)
            height: Display height (default 280)
        """
        self.width = width
        self.height = height
        self.image = Image.new("RGB", (width, height), color=(0, 0, 0))
        self.draw = ImageDraw.Draw(self.image)
        self.is_initialized = False
        
        # Try to load a monospace font
        self.font_lg = None
        self.font_md = None
        self.font_sm = None
        
        self._load_fonts()

    def _load_fonts(self):
        """Load system fonts for text rendering."""
        try:
            # Try to load DejaVu fonts (commonly available on Raspberry Pi)
            self.font_lg = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 32)
            self.font_md = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 24)
            self.font_sm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 16)
        except (OSError, IOError):
            # Fallback to default font
            self.font_lg = ImageFont.load_default()
            self.font_md = ImageFont.load_default()
            self.font_sm = ImageFont.load_default()

    def init(self) -> bool:
        """Initialize the display hardware.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # In a real implementation, this would initialize SPI and GPIO
            # For testing, we'll check if we can access mock hardware
            self.is_initialized = True
            return True
        except Exception as e:
            print(f"❌ Failed to initialize LCD: {e}")
            return False

    def clear(self, color=(0, 0, 0)):
        """Clear the display with a background color.
        
        Args:
            color: RGB tuple (default black)
        """
        self.image = Image.new("RGB", (self.width, self.height), color=color)
        self.draw = ImageDraw.Draw(self.image)

    def draw_text(self, x, y, text, color=(0, 255, 0), font="md", center=False):
        """Draw text on the display.
        
        Args:
            x: X coordinate
            y: Y coordinate
            text: Text to draw
            color: RGB tuple
            font: Font size ("sm", "md", "lg")
            center: Center text horizontally
        """
        font_map = {"sm": self.font_sm, "md": self.font_md, "lg": self.font_lg}
        selected_font = font_map.get(font, self.font_md)
        
        if center:
            bbox = self.draw.textbbox((0, 0), text, font=selected_font)
            text_width = bbox[2] - bbox[0]
            x = (self.width - text_width) // 2
        
        self.draw.text((x, y), text, fill=color, font=selected_font)

    def draw_rectangle(self, x1, y1, x2, y2, color=(0, 255, 0), fill=None):
        """Draw a rectangle on the display.
        
        Args:
            x1, y1, x2, y2: Coordinates
            color: RGB tuple (outline)
            fill: RGB tuple for fill (optional)
        """
        self.draw.rectangle([x1, y1, x2, y2], outline=color, fill=fill)

    def draw_line(self, x1, y1, x2, y2, color=(0, 255, 0), width=1):
        """Draw a line on the display.
        
        Args:
            x1, y1, x2, y2: Coordinates
            color: RGB tuple
            width: Line width
        """
        self.draw.line([(x1, y1), (x2, y2)], fill=color, width=width)

    def draw_waveform(self, samples, x=10, y=100, height=80, color=(0, 255, 0)):
        """Draw a waveform visualization for audio.
        
        Args:
            samples: Audio sample data (normalized 0-1)
            x: Starting X coordinate
            y: Starting Y coordinate  
            height: Height of waveform
            color: RGB tuple
        """
        if not samples or len(samples) < 2:
            return
        
        available_width = self.width - 2 * x
        points_to_draw = min(len(samples), available_width)
        
        for i in range(points_to_draw - 1):
            # Normalize sample to pixel height
            y1 = y + (height // 2) - int(samples[i] * (height // 2))
            y2 = y + (height // 2) - int(samples[i + 1] * (height // 2))
            
            x1 = x + i
            x2 = x + i + 1
            
            self.draw_line(x1, y1, x2, y2, color=color, width=2)

    def update(self):
        """Update the display with current framebuffer.
        
        In a real implementation, this would transfer the PIL image to the LCD.
        """
        if not self.is_initialized:
            return False
        
        try:
            # In a real scenario, we'd use SPI to send the image buffer
            # For now, this is a placeholder
            return True
        except Exception as e:
            print(f"❌ Failed to update display: {e}")
            return False

    def get_image(self):
        """Get the current PIL Image for inspection or saving."""
        return self.image

    def save_screenshot(self, filename="/tmp/jarvis_bud_screenshot.png"):
        """Save a screenshot of the current display.
        
        Args:
            filename: Path to save the PNG
        """
        try:
            self.image.save(filename)
            print(f"📸 Screenshot saved: {filename}")
            return True
        except Exception as e:
            print(f"❌ Failed to save screenshot: {e}")
            return False
