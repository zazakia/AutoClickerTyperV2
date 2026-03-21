import unittest
from unittest.mock import patch, MagicMock
import numpy as np
import cv2
from core.ocr import scan_for_keywords

class TestOCRPreprocessing(unittest.TestCase):
    @patch('core.ocr.capture_screen')
    @patch('core.ocr.pytesseract.image_to_data')
    @patch('core.ocr.config_manager.get')
    def test_scan_for_keywords_preprocessing(self, mock_get, mock_image_to_data, mock_capture_screen):
        mock_get.side_effect = lambda k, d=None: {
            "BLUE_HSV_LOWER": [90, 40, 40],
            "BLUE_HSV_UPPER": [140, 255, 255],
            "ENABLE_COLOR_FILTER": True,
            "COLOR_OVERLAP_THRESHOLD": 0.3,
            "DEBUG_MODE": False,
            "OCR_CONFIDENCE_THRESHOLD": 50,
            "CLICK_KEYWORDS": ["Test"],
            "TYPE_KEYWORDS": [],
        }.get(k, d)

        # Create a blank dark image
        img = np.zeros((200, 200, 3), dtype=np.uint8)
        
        # Add a blue rectangle (RGB). In RGB, blue is [0, 0, 255].
        # It will be converted to BGR [255, 0, 0] internally by cvtColor.
        img[50:150, 50:150] = [0, 0, 255] 
        mock_capture_screen.return_value = img
        
        # Mock OCR output (pytesseract.image_to_data returns dict with 'text' and 'conf')
        mock_image_to_data.return_value = {
            'text': ['Test'],
            'conf': [95],
            'left': [5],
            'top': [5],
            'width': [90],
            'height': [90]
        }
        
        # Test detection logic (preprocessing runs internally before sending to pytesseract)
        results = scan_for_keywords(["Test"], [])
        
        # Ensure that OCR was called (which implies preprocessing ran successfully)
        self.assertTrue(mock_image_to_data.called)
        
        # Ensure it found our mock result (at least one)
        # Tiered PSM might return multiple segments if mock is reused
        self.assertGreaterEqual(len(results), 1)
        found_test = any(m['keyword'] == "Test" for m in results)
        self.assertTrue(found_test)
if __name__ == '__main__':
    unittest.main()
