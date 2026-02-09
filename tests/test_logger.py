
import unittest
import logging
import sys
import os
from unittest.mock import patch

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# We need to be careful importing logger if it auto-configures
from utils.logger import logger, setup_logger, log_action

class TestLogger(unittest.TestCase):
    def test_logger_exists(self):
        self.assertIsInstance(logger, logging.Logger)
        
    @patch('utils.logger.config')
    def test_setup_logger(self, mock_config):
        mock_config.LOG_VERBOSITY = logging.DEBUG
        l = setup_logger()
        self.assertEqual(l.level, logging.DEBUG)
        self.assertTrue(any(isinstance(h, logging.FileHandler) for h in l.handlers))
        self.assertTrue(any(isinstance(h, logging.StreamHandler) for h in l.handlers))

    @patch('utils.logger.logger')
    def test_log_action(self, mock_logger):
        log_action("CLICK", "TestKey", (0,0,0,0), "PASS", 1, 50)
        mock_logger.info.assert_called()
        # Verify message format contains key elements
        args, _ = mock_logger.info.call_args
        msg = args[0]
        self.assertIn("ACTION", msg)
        self.assertIn("CLICK", msg)
        self.assertIn("TestKey", msg)
        self.assertIn("PASS", msg)
        self.assertIn("RETRY", msg)
        self.assertIn("COMPLETION", msg)

    @patch('utils.logger.logging.FileHandler')
    def test_setup_logger_file_permission_error(self, mock_file_handler):
        # Simulate permission error
        mock_file_handler.side_effect = PermissionError("Access denied")
        
        # Should not raise exception, just log warning to console
        logger = setup_logger()
        
        # Verify we still have a logger
        self.assertIsInstance(logger, logging.Logger)
        # Verify console handler is still there (it always adds console first)
        self.assertTrue(len(logger.handlers) >= 1)

if __name__ == '__main__':
    unittest.main()
