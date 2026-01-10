import unittest
from unittest.mock import MagicMock, patch, call
import tkinter as tk
import gui
import logging

class TestAutoClickerGUI(unittest.TestCase):
    def setUp(self):
        # Suppress logging during tests
        logging.getLogger("AutoClicker").setLevel(logging.CRITICAL)
        
        # Setup headless root
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = gui.AutoClickerGUI(self.root)

    def tearDown(self):
        self.root.destroy()

    @patch('gui.gw.getWindowsWithTitle')
    @patch('gui.pyautogui.write')
    @patch('gui.pyautogui.press')
    @patch('gui.time.sleep')
    def test_workflow_execution(self, mock_sleep, mock_press, mock_write, mock_get_win):
        """Verify that inputs are correctly passed to pyautogui functions"""
        
        # Setup inputs
        self.app.project_name_var.set("TestApp")
        self.app.prompt_text.insert("1.0", "Hello World")
        self.app.suffix_var.set("SUFFIX_CMD")
        
        # Setup Mock Window
        mock_win = MagicMock()
        mock_win.title = "TestApp - Main"
        mock_win.isActive = False
        mock_get_win.return_value = [mock_win]
        
        # Run
        self.app.run_workflow()
        
        # Verify Window Finding
        mock_get_win.assert_called_with("TestApp")
        
        # Verify Activation
        # Checks if either .activate() or .minimize()/.restore() was called
        self.assertTrue(mock_win.activate.called or (mock_win.minimize.called and mock_win.restore.called))
        
        # Verify Typing Sequence
        # 1. Prompt "Hello World"
        # 2. Space " "
        # 3. Suffix "SUFFIX_CMD"
        expected_calls = [
            call("Hello World", interval=0.01),
            call(" "),
            call("SUFFIX_CMD", interval=0.05)
        ]
        mock_write.assert_has_calls(expected_calls)
        
        # Verify Send
        mock_press.assert_called_with('enter')
        
    @patch('gui.gw.getWindowsWithTitle')
    def test_workflow_no_window(self, mock_get_win):
        """Verify that nothing happens if window is not found"""
        mock_get_win.return_value = []
        
        self.app.project_name_var.set("MissingApp")
        self.app.run_workflow()
        
        mock_get_win.assert_called_with("MissingApp")
        # Ensure no crash

if __name__ == '__main__':
    unittest.main()
