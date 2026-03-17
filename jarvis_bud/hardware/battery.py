"""PiSugar 3 Battery Manager for Jarvis-Bud."""

import socket
import json
from typing import Optional, Dict


class Battery:
    """
    PiSugar 3 battery manager via /tmp/pisugar-server.sock Unix socket.
    Provides real-time battery percentage, voltage, and charging status.
    """

    def __init__(self, socket_path="/tmp/pisugar-server.sock"):
        """Initialize battery manager.
        
        Args:
            socket_path: Path to PiSugar server socket
        """
        self.socket_path = socket_path
        self.is_connected = False
        self._battery_level = 0
        self._is_charging = False
        self._voltage = 0.0

    def connect(self) -> bool:
        """Connect to PiSugar server socket.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self._socket.connect(self.socket_path)
            self.is_connected = True
            print(f"🔋 Connected to PiSugar at {self.socket_path}")
            return True
        except FileNotFoundError:
            print(f"⚠️  PiSugar socket not found. Running without battery monitoring.")
            self.is_connected = False
            return False
        except Exception as e:
            print(f"❌ Failed to connect to PiSugar: {e}")
            self.is_connected = False
            return False

    def _send_command(self, command: str) -> Optional[Dict]:
        """Send command to PiSugar server.
        
        Args:
            command: Command string (e.g., "get_status")
            
        Returns:
            JSON response dict or None
        """
        if not self.is_connected:
            return None
        
        try:
            self._socket.sendall((command + "\n").encode())
            response = self._socket.recv(1024).decode().strip()
            return json.loads(response)
        except Exception as e:
            print(f"⚠️  Error communicating with PiSugar: {e}")
            return None

    def get_status(self) -> Dict:
        """Get current battery status.
        
        Returns:
            Dictionary with battery info: 
            {"percentage": float, "voltage": float, "charging": bool}
        """
        if not self.is_connected:
            # Return default values if not connected
            return {
                "percentage": 100.0,
                "voltage": 5.0,
                "charging": False,
                "available": False
            }
        
        try:
            response = self._send_command("get_status")
            if response:
                self._battery_level = response.get("percentage", 0)
                self._voltage = response.get("voltage", 0.0)
                self._is_charging = response.get("charging", False)
                
                return {
                    "percentage": self._battery_level,
                    "voltage": self._voltage,
                    "charging": self._is_charging,
                    "available": True
                }
        except Exception as e:
            print(f"⚠️  Error getting battery status: {e}")
        
        return {
            "percentage": self._battery_level,
            "voltage": self._voltage,
            "charging": self._is_charging,
            "available": False
        }

    def get_battery_percentage(self) -> int:
        """Get battery percentage.
        
        Returns:
            Battery percentage (0-100)
        """
        status = self.get_status()
        return int(status.get("percentage", 0))

    def is_low_battery(self, threshold=15) -> bool:
        """Check if battery is below threshold.
        
        Args:
            threshold: Low battery threshold percentage
            
        Returns:
            True if battery is low
        """
        return self.get_battery_percentage() < threshold

    def is_charging(self) -> bool:
        """Check if device is charging.
        
        Returns:
            True if charging
        """
        status = self.get_status()
        return status.get("charging", False)

    def get_battery_emoji(self) -> str:
        """Get battery status emoji.
        
        Returns:
            Emoji representing battery status
        """
        pct = self.get_battery_percentage()
        is_charging = self.is_charging()
        
        if is_charging:
            return "🔌"
        elif pct >= 80:
            return "🔋"
        elif pct >= 50:
            return "🔋"
        elif pct >= 20:
            return "🪫"
        else:
            return "🪫"

    def get_display_text(self) -> str:
        """Get formatted battery status text for display.
        
        Returns:
            Formatted battery status string with emoji
        """
        pct = self.get_battery_percentage()
        emoji = self.get_battery_emoji()
        
        if self.is_charging():
            return f"{emoji} Charging... {pct}%"
        else:
            return f"{emoji} {pct}%"

    def shutdown(self):
        """Graceful shutdown command (if using PiSugar's auto-shutdown)."""
        if not self.is_connected:
            return False
        
        try:
            self._send_command("poweroff")
            print("⚠️  Shutting down via PiSugar...")
            return True
        except Exception as e:
            print(f"❌ Failed to send shutdown command: {e}")
            return False

    def disconnect(self):
        """Disconnect from PiSugar server."""
        if self.is_connected:
            try:
                self._socket.close()
                self.is_connected = False
            except Exception:
                pass
