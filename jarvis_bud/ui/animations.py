"""Animation system for Jarvis-Bud UI."""

import math
import time
from dataclasses import dataclass
from typing import List


@dataclass
class AnimationFrame:
    """Single animation frame."""
    duration: float  # Duration in seconds
    samples: List[float]  # Audio waveform samples (0.0-1.0)
    frame_number: int


class WaveformAnimator:
    """Generate smooth waveform animations for audio visualization."""
    
    def __init__(self, sample_count=60, animation_fps=60):
        """Initialize waveform animator.
        
        Args:
            sample_count: Number of samples to display
            animation_fps: Animation framerate
        """
        self.sample_count = sample_count
        self.animation_fps = animation_fps
        self.frame_duration = 1.0 / animation_fps
        self._frame_count = 0

    def generate_breathing_waveform(self, intensity=0.5) -> List[float]:
        """Generate a "breathing" waveform that pulses smoothly.
        
        Args:
            intensity: Waveform intensity (0.0-1.0)
            
        Returns:
            List of normalized samples
        """
        samples = []
        time_phase = (self._frame_count % 60) / 60.0  # Cycle every 60 frames
        
        for i in range(self.sample_count):
            # Create a smooth breathing pattern
            x = (i / self.sample_count) * math.pi * 2
            base_wave = math.sin(x)
            
            # Add pulse modulation
            pulse = 0.5 + 0.5 * math.sin(time_phase * math.pi * 2)
            
            # Combine and apply intensity
            sample = (base_wave * 0.5 + pulse * 0.5) * intensity
            samples.append(max(0.0, min(1.0, sample)))
        
        self._frame_count += 1
        return samples

    def generate_from_audio_levels(self, audio_chunks: List[float]) -> List[float]:
        """Generate waveform from real audio level data.
        
        Args:
            audio_chunks: List of audio levels (0.0-1.0)
            
        Returns:
            Smoothed and normalized samples for display
        """
        if not audio_chunks:
            return [0.0] * self.sample_count
        
        # Resample to match sample_count
        samples = []
        chunk_spacing = len(audio_chunks) / self.sample_count
        
        for i in range(self.sample_count):
            chunk_idx = int(i * chunk_spacing)
            chunk_idx = min(chunk_idx, len(audio_chunks) - 1)
            samples.append(audio_chunks[chunk_idx])
        
        return samples

    def generate_idle_waveform(self) -> List[float]:
        """Generate an idle/standby waveform pattern.
        
        Returns:
            List of samples representing idle state
        """
        return self.generate_breathing_waveform(intensity=0.2)

    def generate_listening_waveform(self, audio_level: float = 0.5) -> List[float]:
        """Generate actively listening waveform.
        
        Args:
            audio_level: Current audio input level (0.0-1.0)
            
        Returns:
            Animated listening pattern
        """
        samples = []
        time_phase = (self._frame_count % 30) / 30.0
        
        for i in range(self.sample_count):
            # Create vertical bars that respond to audio
            x = (i / self.sample_count) * math.pi * 2
            
            # Responsive movement based on audio level
            animation_speed = 1.0 + audio_level * 2.0
            wave = math.sin(x + time_phase * math.pi * 2 * animation_speed)
            
            # Audio modulation
            sample = (wave * 0.3 + audio_level * 0.7)
            samples.append(max(0.0, min(1.0, sample)))
        
        self._frame_count += 1
        return samples

    def generate_thinking_waveform(self) -> List[float]:
        """Generate a 'thinking' animation pattern.
        
        Returns:
            Animated thinking pattern
        """
        samples = []
        time_phase = (self._frame_count % 120) / 120.0
        
        for i in range(self.sample_count):
            # Create a smooth wave that travels across
            wave_position = (i / self.sample_count) - time_phase
            sample = 0.5 + 0.5 * math.sin(wave_position * math.pi * 4)
            
            # Fade in/out from center
            fade = 1.0 - abs(wave_position - 0.5)
            
            samples.append(max(0.0, min(1.0, sample * fade)))
        
        self._frame_count += 1
        return samples

    def generate_loading_bars(self, progress: float = 0.0) -> List[float]:
        """Generate a loading bar animation.
        
        Args:
            progress: Loading progress (0.0-1.0)
            
        Returns:
            Loading bar pattern
        """
        samples = []
        filled_count = int(self.sample_count * progress)
        
        for i in range(self.sample_count):
            if i < filled_count:
                # Filled portion
                samples.append(0.8)
            elif i == filled_count:
                # Growing edge
                grow_phase = (self._frame_count % 10) / 10.0
                samples.append(0.3 + grow_phase * 0.5)
            else:
                # Empty portion
                samples.append(0.1)
        
        self._frame_count += 1
        return samples

    def get_frame(self, animation_type="idle", **kwargs) -> AnimationFrame:
        """Get next animation frame.
        
        Args:
            animation_type: Type of animation ("idle", "listening", "thinking", "loading")
            **kwargs: Additional parameters
            
        Returns:
            AnimationFrame object
        """
        animation_methods = {
            "idle": self.generate_idle_waveform,
            "listening": lambda: self.generate_listening_waveform(kwargs.get("audio_level", 0.5)),
            "thinking": self.generate_thinking_waveform,
            "breathing": lambda: self.generate_breathing_waveform(kwargs.get("intensity", 0.5)),
            "loading": lambda: self.generate_loading_bars(kwargs.get("progress", 0.0)),
        }
        
        animator = animation_methods.get(animation_type, self.generate_idle_waveform)
        samples = animator()
        
        return AnimationFrame(
            duration=self.frame_duration,
            samples=samples,
            frame_number=self._frame_count
        )

    def reset(self):
        """Reset animation frame counter."""
        self._frame_count = 0
