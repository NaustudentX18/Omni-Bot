"""GPIO Button Handler for Jarvis-Bud (Whisplay HAT)."""

from typing import Callable, Optional
import time
import threading


class ButtonHandler:
    """
    GPIO button interface for Whisplay HAT buttons.
    Button A (GPIO 17): Listen/Wake
    Button B (GPIO 27): Cycle Personalities/Modes + Long-press emergency stop
    """

    def __init__(self, button_a_gpio=17, button_b_gpio=27, long_press_seconds: float = 2.0):
        """Initialize button handler.
        
        Args:
            button_a_gpio: GPIO pin for button A (listen)
            button_b_gpio: GPIO pin for button B (cycle personalities)
        """
        self.button_a_gpio = button_a_gpio
        self.button_b_gpio = button_b_gpio
        
        self._button_a_callback: Optional[Callable] = None
        self._button_b_callback: Optional[Callable] = None
        self._button_b_long_callback: Optional[Callable] = None
        self._long_press_seconds = long_press_seconds
        self._callback_lock = threading.Lock()
        
        self.is_initialized = False
        self._use_mock = False
        self._try_initialize()

    def _try_initialize(self):
        """Try to initialize GPIO, fall back to mock if unavailable."""
        try:
            import RPi.GPIO as GPIO
            
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.button_a_gpio, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(self.button_b_gpio, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            
            # Add event detection
            GPIO.add_event_detect(
                self.button_a_gpio,
                GPIO.FALLING,
                callback=self._handle_button_a,
                bouncetime=300
            )
            GPIO.add_event_detect(
                self.button_b_gpio,
                GPIO.FALLING,
                callback=self._handle_button_b,
                bouncetime=80
            )
            
            self.is_initialized = True
            print(f"🔘 GPIO buttons initialized (A={self.button_a_gpio}, B={self.button_b_gpio})")
            
        except ImportError:
            print("⚠️  RPi.GPIO not available. Using mock button mode.")
            self._use_mock = True
            self.is_initialized = True
        except Exception as e:
            print(f"⚠️  Failed to initialize GPIO: {e}. Using mock mode.")
            self._use_mock = True
            self.is_initialized = True

    def _handle_button_a(self, channel=None):
        """Internal handler for Button A (Listen)."""
        if self._button_a_callback:
            self._button_a_callback()

    def _handle_button_b(self, channel=None):
        """Internal handler for Button B with long-press detection."""
        with self._callback_lock:
            press_duration = 0.0
            if not self._use_mock:
                try:
                    import RPi.GPIO as GPIO

                    start = time.monotonic()
                    # Spin briefly until release to classify press type.
                    while GPIO.input(self.button_b_gpio) == 0 and press_duration < (self._long_press_seconds + 1.0):
                        time.sleep(0.02)
                        press_duration = time.monotonic() - start
                except Exception:
                    press_duration = 0.0

            if press_duration >= self._long_press_seconds and self._button_b_long_callback:
                self._button_b_long_callback()
                return

            if self._button_b_callback:
                self._button_b_callback()

    def on_button_a(self, callback: Callable):
        """Register callback for Button A (Listen).
        
        Args:
            callback: Function to call when button A is pressed
        """
        self._button_a_callback = callback
        print("🤝 Button A callback registered (Listen)")

    def on_button_b(self, callback: Callable):
        """Register callback for Button B (Cycle Personalities).
        
        Args:
            callback: Function to call when button B is pressed
        """
        self._button_b_callback = callback
        print("🤝 Button B callback registered (Cycle Buds)")

    def on_button_b_long_press(self, callback: Callable):
        """Register callback for Button B long-press emergency action."""
        self._button_b_long_callback = callback
        print(f"🤝 Button B long-press callback registered ({self._long_press_seconds:.1f}s)")

    def get_button_a_state(self) -> bool:
        """Get current state of Button A.
        
        Returns:
            True if pressed, False if not
        """
        if self._use_mock:
            return False
        
        try:
            import RPi.GPIO as GPIO
            return GPIO.input(self.button_a_gpio) == 0  # Inverted (pull-up)
        except Exception:
            return False

    def get_button_b_state(self) -> bool:
        """Get current state of Button B.
        
        Returns:
            True if pressed, False if not
        """
        if self._use_mock:
            return False
        
        try:
            import RPi.GPIO as GPIO
            return GPIO.input(self.button_b_gpio) == 0  # Inverted (pull-up)
        except Exception:
            return False

    def simulate_button_a(self):
        """Simulate Button A press (for testing)."""
        print("🔘 Simulating Button A press...")
        self._handle_button_a()

    def simulate_button_b(self):
        """Simulate Button B press (for testing)."""
        print("🔘 Simulating Button B press...")
        self._handle_button_b()

    def simulate_button_b_long_press(self):
        """Simulate Button B long press (for tests and non-GPIO environments)."""
        print("🔘 Simulating Button B long press...")
        if self._button_b_long_callback:
            self._button_b_long_callback()

    def cleanup(self):
        """Clean up GPIO resources."""
        if self._use_mock:
            return
        
        try:
            import RPi.GPIO as GPIO
            GPIO.cleanup([self.button_a_gpio, self.button_b_gpio])
            print("🔘 GPIO buttons cleaned up")
        except Exception as e:
            print(f"⚠️  Error cleaning up GPIO: {e}")
