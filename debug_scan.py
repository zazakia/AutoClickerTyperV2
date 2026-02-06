import os
import sys
import cv2
import numpy as np
import pygetwindow as gw
import pyautogui
from PIL import Image

# Add project root to path
sys.path.append(os.getcwd())

from core.ocr import scan_for_keywords, detect_blue_regions, capture_screen
from core.config_manager import config_manager
from utils.logger import setup_logger
import logging

logger = setup_logger()
logger.setLevel(logging.DEBUG)

def debug_scan():
    title = "Auto Clicker Test Harness"
    config_manager.set("TARGET_WINDOW_TITLE", title)
    click_kw = config_manager.get("CLICK_KEYWORDS")
    type_kw = config_manager.get("TYPE_KEYWORDS")
    
    print(f"Targeting: {title}")
    
    wins = gw.getWindowsWithTitle(title)
    if not wins:
        print(f"ERROR: Window '{title}' not found.")
        return
        
    win = wins[0]
    region = (win.left, win.top, win.width, win.height)
    print(f"Window Region: {region}")
    
    # 1. Running Actual Scan
    matches = scan_for_keywords(click_kw, type_kw)
    
    print(f"\nFound {len(matches)} matches:")
    for m in matches:
        print(f" - {m['keyword']} (found: '{m['found_text']}') at {m['box']} conf {m['conf']}")

if __name__ == "__main__":
    debug_scan()
