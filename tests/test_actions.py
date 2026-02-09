
import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.actions import perform_click, perform_type, perform_shortcut
from core.exceptions import ActionError

class TestActions(unittest.TestCase):
    def setUp(self):
        # Suppress logging
        self.log_patcher = patch('core.actions.logger')
        self.mock_logger = self.log_patcher.start()

    def tearDown(self):
        self.log_patcher.stop()

    @patch('core.actions.pyautogui')
    @patch('core.actions.time')
    def test_perform_click_basic(self, mock_time, mock_pyautogui):
        # Setup
        box = (100, 100, 50, 50) # x, y, w, h
        
        # Execute
        target_x, target_y = perform_click(box)
        
        # Verify
        # Check if coordinates are within bounds + offset
        # (100 + 10%*50) to (100 + 90%*50) -> 105 to 145
        self.assertTrue(105 <= target_x <= 145)
        self.assertTrue(105 <= target_y <= 145)
        
        # Verify calls
        mock_pyautogui.moveTo.assert_called() # Should call smooth_move -> moveTo
        mock_pyautogui.click.assert_called_once()
        self.assertTrue(mock_time.sleep.call_count >= 2) # Pre-click and post-click

    @patch('core.actions.perform_click')
    @patch('core.actions.pyautogui')
    @patch('core.actions.time')
    def test_perform_type_success(self, mock_time, mock_pyautogui, mock_perform_click):
        # Setup
        box = (10, 10, 10, 10)
        keyword = "test input"
        
        # Execute
        result = perform_type(keyword, box)
        
        # Verify
        self.assertTrue(result)
        mock_perform_click.assert_called_with(box)
        mock_pyautogui.write.assert_called_with(keyword, interval=unittest.mock.ANY)
        mock_pyautogui.press.assert_called_with('enter')

    @patch('core.actions.pyautogui')
    def test_perform_shortcut_success(self, mock_pyautogui):
        keys = ['ctrl', 'c']
        result = perform_shortcut(keys)
        self.assertTrue(result)
        mock_pyautogui.hotkey.assert_called_with('ctrl', 'c')

    @patch('core.actions.pyautogui')
    def test_perform_shortcut_failure(self, mock_pyautogui):
        mock_pyautogui.hotkey.side_effect = Exception("Keyboard error")
        
        # Now expects ActionError instead of False
        with self.assertRaises(ActionError):
             perform_shortcut(['ctrl', 'v'])

    @patch('core.actions.pyautogui')
    @patch('core.actions.time')
    def test_perform_click_failure(self, mock_time, mock_pyautogui):
        # Simulate PyAutoGUI error (e.g. FailSafeException)
        mock_pyautogui.moveTo.side_effect = Exception("FailSafeTriggered")
        with self.assertRaises(ActionError):
            perform_click((0,0,10,10))

if __name__ == '__main__':
    unittest.main()
