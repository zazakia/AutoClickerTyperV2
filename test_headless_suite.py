import sys
import unittest
import importlib
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

    print("\n[1/6] Running test_blue_detection...")
    if test_blue_detection.test_blue_detection():
        print("PASS")
    else:
        print("FAIL")

    # List of unit test modules
    test_modules = [
        ('test_gui_unit', 'test_gui_unit'),
        ('test_actions', 'tests.test_actions'),
        ('test_config', 'tests.test_config'),
        ('test_verification', 'tests.test_verification'),
        ('test_logger', 'tests.test_logger'),
        ('test_ocr', 'tests.test_ocr')
    ]

    total_failures = 0


    for idx, (name, module_name) in enumerate(test_modules):
        print(f"\n[{idx+2}/6] Running {name}...")
        try:
            module = importlib.import_module(module_name)
            suite = unittest.TestLoader().loadTestsFromModule(module)
            runner = unittest.TextTestRunner(verbosity=1)
            result = runner.run(suite)
            if result.testsRun == 0:
                 print("NO TESTS RAN (Check discovery)")
                 # Treat as potential warning or failure? 
                 # For now let's just log it.
            if not result.wasSuccessful():
                total_failures += 1
        except ImportError as e:
            print(f"Failed to import {module_name}: {e}")
            total_failures += 1
        except Exception as e:
            print(f"Error running {module_name}: {e}")
            total_failures += 1

    if total_failures == 0:
        print("\nALL TESTS PASSED")
        sys.exit(0)
    else:
        print(f"\n{total_failures} MODULES FAILED")
        sys.exit(1)
