import json
import os
import logging
from typing import Dict, Any, List
from contextlib import suppress
from core.exceptions import ConfigError

import sys

logger = logging.getLogger(__name__)

def get_base_path():
    """Returns the base path for persistent data.
    In frozen (EXE) mode, this is the directory of the executable.
    In script mode, this is the project root.
    """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    # Return current directory if not frozen, which is project root in dev
    return os.getcwd()

def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class ConfigManager:
    """
    Manages application configuration, loading from and saving to a JSON file.
    Falls back to defaults if file doesn't exist.
    """
    
    DEFAULT_CONFIG = {
        "TARGET_WINDOW_TITLE": "",
        "CLICK_KEYWORDS": ["Accept", "Allow", "Allow Always", "Proceed", "Yes", "OK", "Confirm", "Continue", "Expand"],
        "TYPE_KEYWORDS": ["proceed"],
        "OCR_CONFIDENCE_THRESHOLD": 60,
        "SCAN_INTERVAL": 0.5,
        "MAX_RETRY_ATTEMPTS": 3,
        "ACTION_DELAY": 0.1,
        "ALWAYS_ON_TOP": True,
        "ENABLE_COLOR_FILTER": True,
        "BLUE_HSV_LOWER": [100, 50, 50],
        "BLUE_HSV_UPPER": [130, 255, 255],
        "COLOR_OVERLAP_THRESHOLD": 0.5,
        "DEFAULT_SUFFIX": "Proceed",
        "APP_TITLE": "Zapweb.app Prompt Assist and AutoClicker"
    }


    def __init__(self, filename: str = "config.json"):
        self.base_path = get_base_path()
        self.config_path = os.path.join(self.base_path, filename)
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
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse config from {self.config_path}: {e}")
                # We raise ConfigError so the main app knows config is bad
                raise ConfigError(f"Invalid JSON in config file: {e}")
            except Exception as e:
                logger.error(f"Failed to load config from {self.config_path}: {e}")
                # Optional: could raise here too, but maybe file permission error is recoverable?
                # For now let's raise for robustness as requested
                raise ConfigError(f"Could not load config file: {e}")
        else:
            # Fallback to bundled config if available
            bundled_path = get_resource_path(os.path.basename(self.config_path))
            if os.path.exists(bundled_path):
                try:
                    with open(bundled_path, 'r') as f:
                        bundled_config = json.load(f)
                        self._config.update(bundled_config)
                    logger.info(f"Using bundled configuration as default: {bundled_path}")
                    self.save_config() # Persist bundled config to external file
                except Exception as e:
                    logger.error(f"Failed to load bundled config: {e}")
            else:
                logger.info("No config file found and no bundled config. Using hardcoded defaults.")
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
