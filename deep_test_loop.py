import customtkinter as ctk
import threading
import time
import pyautogui
import pygetwindow as gw
from core.config_manager import config_manager
import main
from utils.logger import logger

# Global results
CLICKS = []
TEST_WINDOW_TITLE = "Google Antigravity"

class RobustHarness(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(TEST_WINDOW_TITLE)
        self.geometry("600x400+100+100")
        self.attributes("-topmost", True)
        
        self.label = ctk.CTkLabel(self, text="UNIVERSAL CLICK HARNESS", font=("Arial", 20, "bold"))
        self.label.pack(pady=20)
        
        self.btn = ctk.CTkButton(self, text="Confirm", fg_color="blue", width=200, height=80)
        self.btn.place(x=200, y=150)
        
        # Bind any click on the window
        self.bind("<Button-1>", self.on_any_click)
        # Also bind specifically to the button's internal widgets if needed, 
        # but Button-1 on the root should catch it if not handled.
        
        self.log = ctk.CTkTextbox(self, height=100)
        self.log.pack(side="bottom", fill="x", padx=10, pady=10)

    def on_any_click(self, event):
        # Coordinates recorded are screen coordinates
        x, y = pyautogui.position()
        CLICKS.append(("AUTO_DETECT", x, y))
        msg = f"PHASE 1 - CLICK DETECTED AT SCREEN: ({x}, {y})"
        self.log.insert("end", msg + "\n")
        print(msg)

def run_bot():
    config_manager.set("TARGET_WINDOW_TITLE", TEST_WINDOW_TITLE)
    config_manager.set("CLICK_KEYWORDS", ["Confirm"])
    config_manager.set("OCR_CONFIDENCE_THRESHOLD", 20)
    config_manager.set("SCAN_INTERVAL", 0.5)
    config_manager.set("DEBUG_MODE", False)
    main.stop_event.clear()
    main.main()

if __name__ == "__main__":
    harness = RobustHarness()
    
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    def monitor():
        time.sleep(30)
        print("\n=== DEEP TEST FINAL VERIFICATION ===")
        try:
            win = gw.getWindowsWithTitle(TEST_WINDOW_TITLE)[0]
            bounds = (win.left, win.top, win.left + win.width, win.top + win.height)
            print(f"Window Bounds: {bounds}")
            
            if not CLICKS:
                print("RESULT: FAILED - No clicks detected on harness window.")
            else:
                passed = 0
                for _, cx, cy in CLICKS:
                    if bounds[0] <= cx <= bounds[2] and bounds[1] <= cy <= bounds[3]:
                        print(f"SUCCESS: Click at ({cx}, {cy}) is WITHIN window bounds.")
                        passed += 1
                    else:
                        print(f"FAILURE: Click at ({cx}, {cy}) is OUTSIDE window bounds!")
                
                if passed > 0:
                    print(f"\nFINAL STATUS: PROVEN WORKING ({passed} successful clicks)")
                else:
                    print("\nFINAL STATUS: FAILED (Clicks were outside)")
        except Exception as e:
            print(f"Error during verification: {e}")
            
        main.stop_event.set()
        harness.quit()

    threading.Thread(target=monitor, daemon=True).start()
    harness.mainloop()
