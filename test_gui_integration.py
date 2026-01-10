import unittest
from unittest.mock import patch, MagicMock
import tkinter as tk
import threading
import time
import gui
import main
import logging

class TestGuiIntegration(unittest.TestCase):
    def setUp(self):
        # Suppress logging
        logging.getLogger("AutoClicker").setLevel(logging.CRITICAL)
        
        # Ensure we are using the same main module
        import importlib
        importlib.reload(gui)
        
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = gui.AutoClickerGUI(self.root)
        
        # Ensure stop event is set initially so we don't accidentally run
        main.stop_event.set()

    def tearDown(self):
        # Clean up
        if self.app.autoclicker_thread and self.app.autoclicker_thread.is_alive():
            main.stop_event.set()
            self.app.autoclicker_thread.join(timeout=2)
        self.root.destroy()

    @patch('main.main')
    def test_toggle_lifecycle(self, mock_main):
        """
        Verify that clicking the toggle button:
        1. Clears stop_event (Start)
        2. Starts a thread running main.main
        3. Sets stop_event (Stop)
        4. Waits for thread to finish
        """
        # --- PHASE 1: START ---
        
        # Mock main to just wait until stopped, so checking is_alive works
        def fake_main():
            while not main.stop_event.is_set():
                time.sleep(0.01)
        mock_main.side_effect = fake_main

        # 1. Start execution
        self.app.toggle_autoclicker()
        
        # Verify Event Cleared
        self.assertFalse(main.stop_event.is_set(), "stop_event should be cleared on start")
        
        # Verify Thread Started
        self.assertIsNotNone(self.app.autoclicker_thread)
        self.assertTrue(self.app.autoclicker_thread.is_alive(), "Thread should be running")
        
        # Verify Button Update (Start -> Stop)
        # Note: We need to update idle tasks to ensure config was applied, though usually instant in unit test
        self.root.update_idletasks() 
        self.assertIn("Stop", self.app.toggle_btn.cget('text'))

        # --- PHASE 2: STOP ---
        
        # 2. Stop execution
        self.app.toggle_autoclicker()
        
        # Verify Event Set
        self.assertTrue(main.stop_event.is_set(), "stop_event should be set on stop")
        
        # Wait for thread to actually die (simulating clean shutdown)
        # The GUI waits in a separate thread, so we wait here in main test thread
        self.app.autoclicker_thread.join(timeout=1.0)
        self.assertFalse(self.app.autoclicker_thread.is_alive(), "Thread should have stopped")
        
        # The GUI update happens in root.after, let's process it
        # Poll for the button text update
        for _ in range(10):
            self.root.update()
            if "Start" in self.app.toggle_btn.cget('text'):
                break
            time.sleep(0.1)
        
        # Verify Button Reset (Stop -> Start)
        self.assertIn("Start", self.app.toggle_btn.cget('text'))

if __name__ == "__main__":
    import sys
    with open("integration_test_result.txt", "w") as f:
        runner = unittest.TextTestRunner(stream=f, verbosity=2)
        res = unittest.main(testRunner=runner, exit=False)
        if not res.result.wasSuccessful():
            sys.exit(1)

