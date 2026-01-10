from core.config_manager import config_manager
import os
import json

def test_config():
    print("Testing ConfigManager...")
    # 1. Check if defaults are loaded
    assert config_manager.get("TARGET_WINDOW_TITLE") == "Manager"
    
    # 2. Modify and Save
    config_manager.set("TEST_KEY", "TEST_VALUE")
    
    # 3. Verify file exists
    if not os.path.exists("config.json"):
        print("FAIL: config.json not created.")
        return
        
    # 4. Read file directly
    with open("config.json", "r") as f:
        data = json.load(f)
        if data.get("TEST_KEY") != "TEST_VALUE":
            print("FAIL: Persistence failed.")
            return

    print("PASS: ConfigManager functioning.")

def test_ocr_import():
    print("Testing OCR Import...")
    try:
        from core.ocr import scan_for_keywords
        print("PASS: OCR module imported successfully (Fuzzy match dependencies likely okay).")
    except ImportError as e:
        print(f"FAIL: OCR import failed: {e}")

if __name__ == "__main__":
    test_config()
    test_ocr_import()
