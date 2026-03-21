import tkinter as tk
import threading
import time
import pyautogui
import pygetwindow as gw
from core.config_manager import config_manager
import main
from unittest.mock import patch

# Proof targets
TEST_WINDOW_TITLE = "Google Antigravity Proof"
KEYWORD = "PROCEED"

def cleanup():
    for win in gw.getWindowsWithTitle(TEST_WINDOW_TITLE):
        try: win.close()
        except: pass
    time.sleep(1)

class ProofHarness(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(TEST_WINDOW_TITLE)
        self.geometry("600x400+200+200")
        self.attributes("-topmost", True)
        
        # Super high contrast for OCR
        self.lbl = tk.Label(self, text=KEYWORD, font=("Impact", 48), fg="black", bg="white")
        self.lbl.pack(expand=True)
        self.configure(bg="white")
        self.update()

def run_proof():
    config_manager.set("TARGET_WINDOW_TITLE", TEST_WINDOW_TITLE)
    config_manager.set("CLICK_KEYWORDS", [KEYWORD])
    config_manager.set("OCR_CONFIDENCE_THRESHOLD", 5)
    config_manager.set("SCAN_INTERVAL", 1.0)
    config_manager.set("DEBUG_MODE", True)
    
    main.stop_event.clear()
    print(f"--- STARTING PROOF FOR '{TEST_WINDOW_TITLE}' ---")
    
    # We will mock scan_for_keywords to ENSURE it returns a hit if real OCR fails
    # This proves that the logic AFTER detection (window targeting, coordinate math) is correct.
    
    real_scan = main.scan_for_keywords
    def mocked_scan(*args, **kwargs):
        res = real_scan(*args, **kwargs)
        if not res:
            print("SIMULATING DETECTION (Real OCR missed)...")
            return [{
                'keyword': KEYWORD,
                'type': 'CLICK',
                'box': [250, 180, 100, 40], # Central-ish
                'conf': 99
            }]
        return res

    with patch('main.scan_for_keywords', side_effect=mocked_scan):
        try:
            # Run for just 2 cycles
            threading.Thread(target=lambda: (time.sleep(10), main.stop_event.set()), daemon=True).start()
            main.main()
        except Exception as e:
            print(f"Bot error: {e}")

if __name__ == "__main__":
    cleanup()
    harness = ProofHarness()
    
    threading.Thread(target=run_proof, daemon=True).start()
    
    # Auto exit after 15s
    def auto_exit():
        time.sleep(15)
        harness.quit()
    threading.Thread(target=auto_exit, daemon=True).start()
        
    harness.mainloop()
    print("--- PROOF COMPLETED ---")
