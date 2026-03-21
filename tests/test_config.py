
import unittest
import json
import os
import sys
import tempfile
from unittest.mock import patch, MagicMock, mock_open

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.config_manager import ConfigManager, get_base_path, get_resource_path
from core.exceptions import ConfigError


class TestGetBasePath(unittest.TestCase):
    """Tests for the get_base_path() helper."""

    def test_returns_cwd_when_not_frozen(self):
        """In normal script mode, base path should be cwd."""
        # Ensure sys.frozen is not set
        with patch.dict(sys.__dict__, {}, clear=False):
            if hasattr(sys, 'frozen'):
                del sys.frozen
            result = get_base_path()
        self.assertEqual(result, os.getcwd())

    def test_returns_executable_dir_when_frozen(self):
        """In PyInstaller frozen mode, base path should be executable's directory."""
        fake_exe = r'C:\App\autoclicker.exe'
        with patch.object(sys, 'frozen', True, create=True), \
             patch.object(sys, 'executable', fake_exe):
            result = get_base_path()
        self.assertEqual(result, os.path.dirname(fake_exe))


class TestGetResourcePath(unittest.TestCase):
    """Tests for the get_resource_path() helper."""

    def test_returns_joined_path_when_not_frozen(self):
        """Without _MEIPASS, returns abspath join from current dir."""
        if hasattr(sys, '_MEIPASS'):
            del sys._MEIPASS
        result = get_resource_path('assets/icon.png')
        self.assertEqual(result, os.path.join(os.path.abspath('.'), 'assets/icon.png'))

    def test_returns_meipass_path_when_frozen(self):
        """With _MEIPASS set (PyInstaller), returns path under _MEIPASS."""
        with patch.object(sys, '_MEIPASS', r'C:\App\_internal', create=True):
            result = get_resource_path('assets/icon.png')
        self.assertEqual(result, os.path.join(r'C:\App\_internal', 'assets/icon.png'))


class TestConfigManager(unittest.TestCase):
    """Tests for the ConfigManager class."""

    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.patcher = patch('core.config_manager.get_base_path', return_value=self.test_dir.name)
        self.mock_base_path = self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.test_dir.cleanup()

    # ------------------------------------------------------------------
    # load_config
    # ------------------------------------------------------------------

    def test_load_valid_config_file(self):
        """ConfigManager reads and merges a valid JSON config file."""
        config_data = {"SCAN_INTERVAL": 1.5, "MAX_RETRY_ATTEMPTS": 10}
        path = os.path.join(self.test_dir.name, 'config.json')
        with open(path, 'w') as f:
            json.dump(config_data, f)

        cm = ConfigManager()
        self.assertEqual(cm.get('SCAN_INTERVAL'), 1.5)
        self.assertEqual(cm.get('MAX_RETRY_ATTEMPTS'), 10)

    def test_load_bad_json_raises_config_error(self):
        """Malformed JSON in config file raises ConfigError."""
        path = os.path.join(self.test_dir.name, 'config.json')
        with open(path, 'w') as f:
            f.write("{invalid: json}")

        with self.assertRaises(ConfigError):
            ConfigManager()

    def test_no_config_file_uses_defaults_and_creates_file(self):
        """When no config.json exists and no bundled config, uses defaults and creates file."""
        # Also patch get_resource_path so bundled path doesn't exist
        with patch('core.config_manager.get_resource_path', return_value='/nonexistent/path/config.json'):
            cm = ConfigManager()
        # Default key should be present
        self.assertIn('OCR_CONFIDENCE_THRESHOLD', cm._config)
        # A config.json should have been created in temp dir
        created_path = os.path.join(self.test_dir.name, 'config.json')
        self.assertTrue(os.path.exists(created_path))

    def test_bundled_config_fallback(self):
        """When no user config exists but bundled config does, it is loaded."""
        bundled_data = {"ACTION_DELAY": 0.99}
        bundled_path = os.path.join(self.test_dir.name, 'bundled_config.json')
        with open(bundled_path, 'w') as f:
            json.dump(bundled_data, f)

        with patch('core.config_manager.get_resource_path', return_value=bundled_path):
            cm = ConfigManager()
        self.assertEqual(cm.get('ACTION_DELAY'), 0.99)

    def test_load_config_io_error_raises_config_error(self):
        """An IOError while opening config raises ConfigError."""
        path = os.path.join(self.test_dir.name, 'config.json')
        with open(path, 'w') as f:
            f.write('{}')  # create file so exists check passes

        with patch('builtins.open', side_effect=IOError("disk read error")):
            with self.assertRaises(ConfigError):
                ConfigManager()

    # ------------------------------------------------------------------
    # get()
    # ------------------------------------------------------------------

    def test_get_returns_default_for_missing_key(self):
        """get() returns provided default when key not in config."""
        with patch('core.config_manager.get_resource_path', return_value='/nonexistent'):
            cm = ConfigManager()
        self.assertEqual(cm.get('NONEXISTENT_KEY', 'my_default'), 'my_default')

    def test_get_returns_none_when_no_default(self):
        """get() returns None when key missing and no default given."""
        with patch('core.config_manager.get_resource_path', return_value='/nonexistent'):
            cm = ConfigManager()
        self.assertIsNone(cm.get('REALLY_MISSING_KEY'))

    def test_get_env_var_bool_true(self):
        """get() parses env var 'true' as Python True."""
        with patch('core.config_manager.get_resource_path', return_value='/nonexistent'), \
             patch.dict(os.environ, {'ALWAYS_ON_TOP': 'true'}):
            cm = ConfigManager()
            self.assertIs(cm.get('ALWAYS_ON_TOP'), True)

    def test_get_env_var_bool_false(self):
        """get() parses env var 'false' as Python False."""
        with patch('core.config_manager.get_resource_path', return_value='/nonexistent'), \
             patch.dict(os.environ, {'ENABLE_COLOR_FILTER': 'false'}):
            cm = ConfigManager()
            self.assertIs(cm.get('ENABLE_COLOR_FILTER'), False)

    def test_get_env_var_int(self):
        """get() parses integer env var correctly."""
        with patch('core.config_manager.get_resource_path', return_value='/nonexistent'), \
             patch.dict(os.environ, {'MAX_RETRY_ATTEMPTS': '7'}):
            cm = ConfigManager()
            self.assertEqual(cm.get('MAX_RETRY_ATTEMPTS'), 7)

    def test_get_env_var_float(self):
        """get() parses float env var correctly."""
        with patch('core.config_manager.get_resource_path', return_value='/nonexistent'), \
             patch.dict(os.environ, {'SCAN_INTERVAL': '0.75'}):
            cm = ConfigManager()
            self.assertEqual(cm.get('SCAN_INTERVAL'), 0.75)

    def test_get_env_var_string(self):
        """get() returns raw string when env var isn't a bool/number."""
        with patch('core.config_manager.get_resource_path', return_value='/nonexistent'), \
             patch.dict(os.environ, {'TARGET_WINDOW_TITLE': 'MyApp'}):
            cm = ConfigManager()
            self.assertEqual(cm.get('TARGET_WINDOW_TITLE'), 'MyApp')

    # ------------------------------------------------------------------
    # set() / save_config()
    # ------------------------------------------------------------------

    def test_set_persists_value_to_file(self):
        """set() updates in-memory config and saves it to disk."""
        with patch('core.config_manager.get_resource_path', return_value='/nonexistent'):
            cm = ConfigManager()
        cm.set('SCAN_INTERVAL', 3.14)

        # Reload from same path to verify
        saved_path = os.path.join(self.test_dir.name, 'config.json')
        with open(saved_path) as f:
            data = json.load(f)
        self.assertEqual(data['SCAN_INTERVAL'], 3.14)
        self.assertEqual(cm.get('SCAN_INTERVAL'), 3.14)

    def test_save_config_handles_permission_error_gracefully(self):
        """save_config() logs error but does NOT raise when file write fails."""
        with patch('core.config_manager.get_resource_path', return_value='/nonexistent'):
            cm = ConfigManager()

        # Make open raise PermissionError only when writing
        original_open = open
        def side_effect_open(path, mode='r', **kwargs):
            if 'w' in str(mode):
                raise PermissionError("Access denied")
            return original_open(path, mode, **kwargs)

        with patch('builtins.open', side_effect=side_effect_open):
            try:
                cm.save_config()  # Should NOT raise
            except PermissionError:
                self.fail("save_config() should not propagate PermissionError")


if __name__ == '__main__':
    unittest.main()
