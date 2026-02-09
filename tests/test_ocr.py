
import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import numpy as np

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.exceptions import OCRError
# Helper to avoid import errors if mss/cv2 not present during test loading (though we have mocks in suite)
# We need to patch them BEFORE importing core.ocr if possible, or patch where used.
# Since ocr.py imports them at top level, we might rely on the suite's sys.modules patches, 
# but for unit test isolation we should patch here too if running standalone.

class TestOCR(unittest.TestCase):
    def setUp(self):
        self.log_patcher = patch('core.ocr.logger')
        self.mock_logger = self.log_patcher.start()

    def tearDown(self):
        self.log_patcher.stop()

    @patch('core.ocr.mss')
    def test_capture_screen_failure(self, mock_mss):
        # Setup mock to raise exception
        mock_sct = MagicMock()
        mock_mss.mss.return_value.__enter__.return_value = mock_sct
        mock_sct.grab.side_effect = Exception("MSS Error")

        from core.ocr import capture_screen
        
        with self.assertRaises(OCRError):
            capture_screen()

    @patch('core.ocr.config_manager')
    @patch('core.ocr.cv2')
    def test_detect_blue_regions_failure(self, mock_cv2, mock_config):
        mock_config.get.return_value = True # Enable filter
        mock_cv2.cvtColor.side_effect = Exception("CV2 Error")
        
        from core.ocr import detect_blue_regions
        
        # Mock image
        mock_img = MagicMock()
        
        with self.assertRaises(OCRError):
            detect_blue_regions(mock_img)

if __name__ == '__main__':
    unittest.main()
