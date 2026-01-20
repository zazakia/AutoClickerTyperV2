import subprocess
import time
import sys
import os
import pyautogui
from core.ocr import scan_for_keywords
from core.config_manager import config_manager

def debug_live():
    print("Launching Harness...")
    h_proc = subprocess.Popen([sys.executable, "test_harness.py"])
    time.sleep(5)
    
    print("Testing Detection...")
    # Manually configure target window to ensure it uses the harness
    config_manager.set("TARGET_WINDOW_TITLE", "Auto Clicker Test Harness")
    
    click_kws = ["Accept", "Run", "Allow", "Proceed", "Confirm", "Continue", "Expand"]
    
    start_time = time.time()
    while time.time() - start_time < 20:
        matches = scan_for_keywords(click_kws, ["proceed"])
        if matches:
            print(f"[{time.time()-start_time:.1f}s] FOUND {len(matches)} matches:")
            for m in matches:
                print(f"  - {m['keyword']} at {m['box']} (Conf: {m['conf']})")
        else:
            print(f"[{time.time()-start_time:.1f}s] No matches found.")
        time.sleep(2)

    h_proc.terminate()

if __name__ == "__main__":
    debug_live()
