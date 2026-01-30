import sys
import unittest
from unittest.mock import MagicMock

# Create mock module for customtkinter
mock_ctk_module = MagicMock()

# Import our mock classes
from tests.headless_mocks import (
    MockCTk, MockCTkFrame, MockCTkLabel, MockCTkButton, MockCTkSwitch,
    MockCTkTabview, MockCTkEntry, MockCTkTextbox, MockCTkSlider,
    MockCTkInputDialog, mock_font
)

# Assign classes to module
mock_ctk_module.CTk = MockCTk
mock_ctk_module.CTkFrame = MockCTkFrame
mock_ctk_module.CTkLabel = MockCTkLabel
mock_ctk_module.CTkButton = MockCTkButton
mock_ctk_module.CTkSwitch = MockCTkSwitch
mock_ctk_module.CTkTabview = MockCTkTabview
mock_ctk_module.CTkEntry = MockCTkEntry
mock_ctk_module.CTkTextbox = MockCTkTextbox
mock_ctk_module.CTkSlider = MockCTkSlider
mock_ctk_module.CTkInputDialog = MockCTkInputDialog
mock_ctk_module.CTkFont = mock_font

# Apply patches
sys.modules['customtkinter'] = mock_ctk_module
sys.modules['pyautogui'] = MagicMock()
sys.modules['mouseinfo'] = MagicMock()
sys.modules['pygetwindow'] = MagicMock()
sys.modules['tkinter'] = MagicMock()

if __name__ == "__main__":
    print("Running headless tests...")

    # Import tests AFTER patching
    import test_blue_detection

    print("\n[1/2] Running test_blue_detection...")
    if test_blue_detection.test_blue_detection():
        print("PASS")
    else:
        print("FAIL")

    print("\n[2/2] Running test_gui_unit...")
    import test_gui_unit
    suite = unittest.TestLoader().loadTestsFromModule(test_gui_unit)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    if result.wasSuccessful():
        print("ALL TESTS PASSED")
        sys.exit(0)
    else:
        print("SOME TESTS FAILED")
        sys.exit(1)
