import unittest
from unittest.mock import MagicMock, patch, call
import customtkinter as ctk
import gui
import logging
import threading

class TestAutoClickerGUI(unittest.TestCase):
    def setUp(self):
        # Suppress logging during tests
        logging.getLogger("AutoClicker").setLevel(logging.CRITICAL)
        
        # Setup App
        # We need to ensure we don't actually start the mainloop or show windows if possible
        self.app = gui.App()
        self.app.withdraw() # Hide window

    def tearDown(self):
        self.app.destroy()

    @patch('gui.gw.getWindowsWithTitle')
    @patch('gui.pyautogui.write')
    @patch('gui.pyautogui.press')
    @patch('gui.time.sleep')
    @patch('gui.scan_for_keywords')
    def test_workflow_execution(self, mock_scan, mock_sleep, mock_press, mock_write, mock_get_win):
        """Verify that inputs are correctly passed to pyautogui functions"""
        
        # Setup inputs
        self.app.target_entry.delete(0, 'end')
        self.app.target_entry.insert(0, "TestApp")
        
        self.app.suffix_entry.delete(0, 'end')
        self.app.suffix_entry.insert(0, "SUFFIX_CMD")
        
        # Setup Mock Window
        mock_win = MagicMock()
        mock_win.title = "TestApp - Main"
        mock_win.isActive = False
        mock_get_win.return_value = [mock_win]
        
        # Mock Scan (Avoid OCR)
        mock_scan.return_value = [] 
        
        # Run
        # gui.run_workflow takes prompt_text
        self.app.run_workflow("Hello World")
        
        # Verify Window Finding
        mock_get_win.assert_called_with("TestApp")
        
        # Verify Activation
        # Checks if either .activate() or .minimize()/.restore() was called
        self.assertTrue(mock_win.activate.called or (mock_win.minimize.called and mock_win.restore.called))
        
        # Verify Typing Sequence
        # 1. Prompt "Hello World"
        # 2. Suffix "SUFFIX_CMD" (appended in local var 'full')
        # Logic in gui.py: 
        # full = prompt_text + " " + suffix
        # pyautogui.write(full)
        
        expected_text = "Hello World SUFFIX_CMD"
        
        mock_write.assert_called_with(expected_text, interval=0.01)
        
        # Verify Send
        mock_press.assert_called_with('enter')
        
    @patch('gui.gw.getWindowsWithTitle')
    def test_workflow_no_window(self, mock_get_win):
        """Verify that nothing happens if window is not found"""
        mock_get_win.return_value = []
        
        self.app.target_entry.delete(0, 'end')
        self.app.target_entry.insert(0, "MissingApp")
        
        self.app.run_workflow("Test")
        
        mock_get_win.assert_called_with("MissingApp")
        # Ensure no crash

if __name__ == '__main__':
    unittest.main()
