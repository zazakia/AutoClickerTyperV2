
import unittest
import json
import os
import tempfile
import sys
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.config_manager import ConfigManager
from core.exceptions import ConfigError

class TestConfigManager(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.config_filename = "test_config.json"
        
        # Patch the base path to point to our temp dir
        self.patcher = patch('core.config_manager.get_base_path', return_value=self.test_dir.name)
        self.mock_base_path = self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.test_dir.cleanup()

    def test_load_bad_json(self):
        # Create a malformed config file
        path = os.path.join(self.test_dir.name, self.config_filename)
        with open(path, 'w') as f:
            f.write("{invalid_json")
            
        # We need to initialize ConfigManager with a file that exists but is bad
        # ConfigManager usually loads 'config.json' from base_path.
        # Let's see if we can instantiate it with a specific file or if it hardcodes.
        # Based on previous views, it likely takes a filename or defaults.
        # Let's look at config_manager.py again if unsure, but I recall it takes config_file args or similar.
        # Wait, Step 281 `utils.logger` uses `config_manager.base_path`.
        
        # Assuming ConfigManager() init tries to load.
        # If I want to test tailored file, I might need to mock open or something.
        # But here I wrote to the actual file path that ConfigManager would look for?
        # If ConfigManager looks for 'config.json', I should write to 'config.json'.
        
        target_file = os.path.join(self.test_dir.name, "config.json")
        with open(target_file, 'w') as f:
            f.write("{invalid: json}")
            
        with self.assertRaises(ConfigError):
            ConfigManager()

if __name__ == '__main__':
    unittest.main()
