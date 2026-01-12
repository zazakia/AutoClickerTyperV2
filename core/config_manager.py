import json
import os
import logging
from typing import Dict, Any, List
from contextlib import suppress

logger = logging.getLogger(__name__)

class ConfigManager:
    """
    Manages application configuration, loading from and saving to a JSON file.
    Falls back to defaults if file doesn't exist.
    """
    
    DEFAULT_CONFIG = {
        "TARGET_WINDOW_TITLE": "Manager",
        "CLICK_KEYWORDS": ["Accept", "Run", "Allow", "Allow Always", "Proceed", "Yes", "OK", "Confirm"],
        "TYPE_KEYWORDS": ["proceed"],
        "OCR_CONFIDENCE_THRESHOLD": 60,
        "SCAN_INTERVAL": 0.5,
        "MAX_RETRY_ATTEMPTS": 3,
        "ACTION_DELAY": 0.1,
        "ALWAYS_ON_TOP": True,
        "ENABLE_COLOR_FILTER": True,
        "BLUE_HSV_LOWER": [100, 50, 50],
        "BLUE_HSV_UPPER": [130, 255, 255],
        "COLOR_OVERLAP_THRESHOLD": 0.5
    }

    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self._config = self.DEFAULT_CONFIG.copy()
        self.load_config()

    def load_config(self):
        """Loads configuration from the file."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    user_config = json.load(f)
                    # Update defaults with user config (preserves new keys if defaults change)
                    self._config.update(user_config)
                logger.info(f"Configuration loaded from {self.config_path}")
            except Exception as e:
                logger.error(f"Failed to load config from {self.config_path}: {e}")
        else:
            logger.info("No config file found. Using defaults.")
            self.save_config() # Create default file

    def save_config(self):
        """Saves current configuration to the file."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self._config, f, indent=4)
            logger.info(f"Configuration saved to {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieves a configuration value, checking environment variables first."""
        # Check environment variable first
        env_val = os.getenv(key)
        if env_val is not None:
            # Try to convert to appropriate type if it looks like a number or boolean
            if env_val.lower() == 'true': return True
            if env_val.lower() == 'false': return False
            with suppress(ValueError):
                if '.' in env_val: return float(env_val)
                return int(env_val)
            return env_val
            
        return self._config.get(key, default)

    def set(self, key: str, value: Any):
        """Sets a configuration value and saves the file."""
        self._config[key] = value
        self.save_config()

# Global Instance
config_manager = ConfigManager()
