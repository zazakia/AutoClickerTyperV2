
import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.verification import verify_action

class TestVerification(unittest.TestCase):
    @patch('core.verification.scan_for_keywords')
    @patch('core.verification.time.sleep') # Don't wait
    def test_verify_action_success(self, mock_sleep, mock_scan):
        # Scenario: Action was to click "Accept". 
        # After action, "Accept" is NOT found at that location.
        # scan_for_keywords returns either empty or keywords elsewhere.
        
        target_keyword = "Accept"
        target_box = (100, 100, 50, 50) # The button we clicked
        
        # Mock finding "Accept" but far away (moved?) or nothing
        mock_scan.return_value = []
        
        verified, reason = verify_action(target_keyword, target_box)
        
        self.assertTrue(verified)
        self.assertIn("is gone", reason)

    @patch('core.verification.scan_for_keywords')
    @patch('core.verification.time.sleep')
    def test_verify_action_failure_overlap(self, mock_sleep, mock_scan):
        # Scenario: "Accept" is still there at the same spot.
        target_keyword = "Accept"
        target_box = (100, 100, 50, 50)
        
        # Mock finding it again at same location
        mock_scan.return_value = [{
            'keyword': 'Accept',
            'box': (105, 105, 40, 40) # Strong overlap
        }]
        
        verified, reason = verify_action(target_keyword, target_box)
        
        self.assertFalse(verified)
        self.assertFalse(verified)
        self.assertIn("Verification Warning", reason)

    @patch('core.verification.scan_for_keywords')
    @patch('core.verification.time.sleep') 
    def test_verify_action_no_overlap(self, mock_sleep, mock_scan):
         # Scenario: "Accept" is found, but completely elsewhere (maybe another button appeared)
        target_keyword = "Accept"
        target_box = (100, 100, 50, 50)
        
        # Found at 500, 500
        mock_scan.return_value = [{
            'keyword': 'Accept',
            'box': (500, 500, 50, 50) 
        }]
        
        verified, reason = verify_action(target_keyword, target_box)
        
        # Should pass because the *original* one is gone
        self.assertTrue(verified)

if __name__ == '__main__':
    unittest.main()
