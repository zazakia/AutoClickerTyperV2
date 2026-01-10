import unittest
from unittest.mock import MagicMock, patch, call
import tkinter as tk
import gui
import sys
import logging

class TestWorkflow(unittest.TestCase):
    def test_run_workflow(self):
        # Setup Logger to avoid clutter
        logging.getLogger("AutoClicker").setLevel(logging.CRITICAL)

        # Mock dependencies
        with patch('gui.gw.getWindowsWithTitle') as mock_get_win, \
             patch('gui.pyautogui.write') as mock_write, \
             patch('gui.pyautogui.press') as mock_press, \
             patch('gui.time.sleep'): # skip sleeps

            # Setup Window Mock
            mock_win = MagicMock()
            mock_win.title = "Target Window"
            mock_win.isActive = False
            mock_get_win.return_value = [mock_win]

            # Initialize App
            root = tk.Tk()
            root.withdraw()
            app = gui.AutoClickerGUI(root)
            
            # Case 1: Valid Input
            app.project_name_var.set("Target Window")
            app.prompt_text.insert("1.0", "My Prompt")
            app.suffix_var.set("MY SUFFIX")
            
            # Execute
            app.run_workflow()
            
            # Verify
            mock_get_win.assert_called_with("Target Window")
            
            # Window focus logic (activate or minimize/restore)
            # We don't strictly care which was called as long as one attempt was made, 
            # but let's check basic interaction
            self.assertTrue(mock_win.activate.called or mock_win.minimize.called)
            
            # Verify typing
            # Expected calls: write("My Prompt", interval=0.01), write(" "), write("MY SUFFIX", interval=0.05)
            mock_write.assert_has_calls([
                call("My Prompt", interval=0.01),
                call(" "),
                call("MY SUFFIX", interval=0.05)
            ])
            
            mock_press.assert_called_with('enter')
            print("TEST: Workflow Logic Verified with Mocks")

    def test_run_workflow_no_window(self):
        # Setup Logger
        logging.getLogger("AutoClicker").setLevel(logging.CRITICAL)

        with patch('gui.gw.getWindowsWithTitle', return_value=[]) as mock_get_win, \
             patch('gui.pyautogui.write') as mock_write:
            
            root = tk.Tk()
            root.withdraw()
            app = gui.AutoClickerGUI(root)
            app.project_name_var.set("NonExistent")
            
            app.run_workflow()
            
            mock_get_win.assert_called_with("NonExistent")
            mock_write.assert_not_called()
            print("TEST: Workflow Aborted correctly when window missing")

if __name__ == "__main__":
    unittest.main()
