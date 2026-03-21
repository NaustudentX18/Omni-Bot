"""WM8960 Audio Codec Driver for Jarvis-Bud."""

import array
import wave


class AudioCodec:
    """
    WM8960 audio codec interface for capturing and playing audio.
    Uses alsaaudio or pyaudio backend.
    """

    def __init__(self, sample_rate=16000, channels=1, chunk_size=1024):
        """Initialize the audio codec.

        Args:
            sample_rate: Audio sample rate in Hz (default 16000)
            channels: Number of channels (default 1 - mono)
            chunk_size: Buffer size for audio chunks
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.is_recording = False
        self._device = None
        self._audio_data = []
        self._backend = None
        self._warned_uninitialized_capture = False

    @property
    def is_initialized(self) -> bool:
        """Whether a usable audio backend is active."""
        return self._backend is not None

    def init(self) -> bool:
        """Initialize the audio codec hardware.

        Returns:
            True if successful, False otherwise
        """
        try:
            # Try to import alsaaudio first (preferred for RPi)
            try:
                import alsaaudio  # noqa: F401

                self._backend = "alsaaudio"
                self._init_alsaaudio()
                return True
            except ImportError:
                # Fallback to pyaudio
                try:
                    import pyaudio  # noqa: F401

                    self._backend = "pyaudio"
                    self._init_pyaudio()
                    return True
                except ImportError:
                    print("⚠️  Neither alsaaudio nor pyaudio found. Audio disabled.")
                    return False
        except Exception as e:
            print(f"❌ Failed to initialize audio codec: {e}")
            return False

    def _init_alsaaudio(self):
        """Initialize alsaaudio backend."""
        import alsaaudio

        # Set ALSA card and PCM device
        self._alsa_capture = alsaaudio.PCM(
            alsaaudio.PCM_CAPTURE, alsaaudio.PCM_NONBLOCK, device="default"
        )
        self._alsa_capture.setchannels(self.channels)
        self._alsa_capture.setrate(self.sample_rate)
        self._alsa_capture.setformat(alsaaudio.PCM_FORMAT_S16_LE)
        self._alsa_capture.setperiodsize(self.chunk_size)

    def _init_pyaudio(self):
        """Initialize pyaudio backend."""
        import pyaudio

        self._pa = pyaudio.PyAudio()
        self._stream = self._pa.open(
            format=pyaudio.paInt16,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk_size,
        )

    def start_recording(self):
        """Start recording audio."""
        if not self.is_initialized:
            return
        self.is_recording = True
        self._audio_data = []

    def stop_recording(self) -> bytes:
        """Stop recording and return audio data.

        Returns:
            Raw audio bytes
        """
        if not self.is_initialized:
            return b""
        self.is_recording = False
        return b"".join(self._audio_data)

    def capture_chunk(self) -> bytes | None:
        """Capture a chunk of audio data.

        Returns:
            Audio chunk bytes or None if no data available
        """
        if not self.is_initialized:
            if not self._warned_uninitialized_capture:
                print("⚠️  Audio backend is not initialized; skipping capture.")
                self._warned_uninitialized_capture = True
            return None

        try:
            if self._backend == "alsaaudio":
                length, data = self._alsa_capture.read()
                if length > 0:
                    return data
            else:  # pyaudio
                try:
                    data = self._stream.read(self.chunk_size, exception_on_overflow=False)
                    return data
                except Exception:
                    return None
        except Exception as e:
            print(f"⚠️  Error capturing audio: {e}")
            return None

        return None

    def record_to_file(self, filename, duration=5) -> bool:
        """Record audio to a WAV file.

        Args:
            filename: Output WAV file path
            duration: Recording duration in seconds

        Returns:
            True if successful
        """
        try:
            self.start_recording()

            frames = []
            for _ in range(0, int(self.sample_rate / self.chunk_size * duration)):
                chunk = self.capture_chunk()
                if chunk:
                    frames.append(chunk)

            self.stop_recording()

            # Write WAV file
            with wave.open(filename, "wb") as wav_file:
                wav_file.setnchannels(self.channels)
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(self.sample_rate)
                wav_file.writeframes(b"".join(frames))

            print(f"🎙️  Audio recorded to {filename}")
            return True
        except Exception as e:
            print(f"❌ Failed to record audio: {e}")
            return False

    def get_audio_level(self) -> float:
        """Get current audio input level (0.0 - 1.0).

        Returns:
            Normalized audio level
        """
        try:
            chunk = self.capture_chunk()
            if not chunk:
                return 0.0

            # Convert bytes to audio samples and calculate RMS
            samples = array.array("h", chunk)
            rms = sum(s * s for s in samples) / len(samples)
            level = (rms**0.5) / 32768.0  # Normalize for 16-bit audio

            return min(1.0, level)
        except Exception:
            return 0.0

    def cleanup(self):
        """Clean up audio resources."""
        try:
            if self._backend == "pyaudio" and hasattr(self, "_stream"):
                self._stream.stop_stream()
                self._stream.close()
                self._pa.terminate()
        except Exception as e:
            print(f"⚠️  Error cleaning up audio: {e}")
