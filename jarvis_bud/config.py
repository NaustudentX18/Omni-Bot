"""Configuration Manager for Jarvis-Bud."""

import json
import os
from typing import Any, Dict, Optional
from pathlib import Path


class ConfigManager:
    """Manage Jarvis-Bud configuration."""

    def __init__(self, config_path: str = "config/config.json"):
        """Initialize config manager.
        
        Args:
            config_path: Path to config.json
        """
        self.config_path = config_path
        self._config: Dict[str, Any] = {}
        self.load()

    def load(self) -> bool:
        """Load configuration from file.
        
        Returns:
            True if successful
        """
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    self._config = json.load(f)
                print(f"📂 Config loaded: {self.config_path}")
                return True
            else:
                print(f"ℹ️  No config found at {self.config_path}")
                return False
        except Exception as e:
            print(f"❌ Error loading config: {e}")
            return False

    def save(self) -> bool:
        """Save configuration to file.
        
        Returns:
            True if successful
        """
        try:
            os.makedirs(os.path.dirname(self.config_path) or ".", exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(self._config, f, indent=2)
            print(f"💾 Config saved: {self.config_path}")
            return True
        except Exception as e:
            print(f"❌ Error saving config: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """Get config value.
        
        Args:
            key: Configuration key (supports dot notation like "bud.name")
            default: Default value if key not found
            
        Returns:
            Config value or default
        """
        keys = key.split(".")
        value = self._config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key: str, value: Any):
        """Set config value.
        
        Args:
            key: Configuration key
            value: Value to set
        """
        keys = key.split(".")
        config = self._config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value

    def get_bud(self) -> Optional[Dict]:
        """Get current Bud configuration.
        
        Returns:
            Bud config dict
        """
        return self.get("bud")

    def get_bud_system_prompt(self) -> str:
        """Get system prompt for current Bud.
        
        Returns:
            System prompt string
        """
        return self.get("bud.system_prompt", "You are a helpful AI assistant.")

    def get_ollama_url(self) -> Optional[str]:
        """Get local Ollama URL.
        
        Returns:
            Ollama server URL or None
        """
        return self.get("connectivity.ollama")

    def get_openrouter_key(self) -> Optional[str]:
        """Get OpenRouter API key.
        
        Returns:
            API key or None
        """
        return self.get("openrouter.api_key")

    def is_configured(self) -> bool:
        """Check if system is configured.
        
        Returns:
            True if config exists and has required fields
        """
        required_fields = ["bud", "hardware"]
        return all(self.get(field) is not None for field in required_fields)

    def get_display_dict(self) -> Dict:
        """Get a clean config dict suitable for display (removes sensitive data).
        
        Returns:
            Config dict with sensitive data redacted
        """
        display_config = json.loads(json.dumps(self._config))
        
        # Redact API keys
        if "openrouter" in display_config and "api_key" in display_config["openrouter"]:
            api_key = display_config["openrouter"]["api_key"]
            display_config["openrouter"]["api_key"] = api_key[:8] + "..." if len(api_key) > 8 else "***"
        
        return display_config

    def print_config(self):
        """Print configuration in a readable format."""
        print("\n" + "="*60)
        print("Current Configuration".center(60))
        print("="*60)
        
        config_dict = self.get_display_dict()
        
        def print_dict(d, indent=0):
            for key, value in d.items():
                if isinstance(value, dict):
                    print("  " * indent + f"📋 {key}:")
                    print_dict(value, indent + 1)
                else:
                    print("  " * indent + f"  • {key}: {value}")
        
        print_dict(config_dict)
        print("="*60 + "\n")
