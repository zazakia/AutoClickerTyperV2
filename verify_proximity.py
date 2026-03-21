import time
import sys
import os
import json
from core.config_manager import config_manager
from core.ocr import scan_for_keywords
from core.actions import perform_click
from utils.logger import logger
import logging

def verify_and_click_proximity():
    logger.setLevel(logging.DEBUG)
    logger.info("Starting Proximity Click Verification...")
    
    import pygetwindow as gw
    import time
    
    # 1. Configuration
    config_manager.set("TARGET_WINDOW_TITLE", "Manager")
    config_manager.set("OCR_CONFIDENCE_THRESHOLD", 30)
    config_manager.set("PROXIMITY_CLICKING_ENABLED", True)
    config_manager.set("PROXIMITY_DIRECTION", "LEFT")
    config_manager.set("ANCHOR_KEYWORDS", ["Co.", "Co", "©", "bell"])
    config_manager.set("CLICK_KEYWORDS", ["Android"])
    
    DPI_SCALE = 1.25
    
    wins = gw.getWindowsWithTitle("Manager")
    target_win = None
    for w in wins:
        if w.title == "Manager":
            target_win = w
            break
            
    if target_win:
        logger.info(f"Targeting window: {target_win.title}")
        try:
            if target_win.isMinimized: target_win.restore()
            target_win.activate()
            time.sleep(2.0)
            logger.info(f"Active window: {gw.getActiveWindow().title}")
        except Exception as e:
            logger.warning(f"Activation failed: {e}")
            
    logger.info("Scanning for proximity match...")
    from core.ocr import get_target_region
    region = get_target_region()
    logger.info(f"Targeting window region: {region}")
    
    # 2. Scan
    anchors = config_manager.get("ANCHOR_KEYWORDS")
    matches_raw, all_segments = scan_for_keywords(config_manager.get("CLICK_KEYWORDS"), anchors, debug_segments=True)
    
    # Save debug image
    from core.ocr import get_target_region, capture_screen
    region = get_target_region()
    screenshot = capture_screen(region=region)
    screenshot.save("debug_screen.png")
    logger.info("Saved debug_screen.png")
    
    # Dump all segments to see what OCR saw
    with open("all_segments_verify.json", "w") as f:
        json.dump([{"text": s[0], "box": s[1], "conf": s[2]} for s in all_segments], f, indent=4)
    # Filter matches to ignore sidebar (x > 1500)
    matches = [m for m in matches_raw if m['box'][0] < 1500]
    
    # Debug logging
    for m in matches:
        logger.info(f"MATCH: {m['keyword']} at {m['box']} text='{m.get('found_text', '')}'")
    
    if not matches:
        logger.warning("No matches found in 'Manager' window.")
        return False
        
    # 3. Filter for proximity matches
    proximity_matches = [m for m in matches if m['keyword'].startswith("Proximity(")]
    
    if not proximity_matches:
        logger.warning("Bell icon found but no text detected to its left (proximity).")
        # List all matches for debugging
        for m in matches:
            logger.debug(f"Match: {m['keyword']} at {m['box']} (Text: {m.get('found_text', 'N/A')})")
        return False
        
    logger.info(f"Found {len(proximity_matches)} proximity matches.")
    
    # 4. Target specific text
    target = None
    for pm in proximity_matches:
        text = pm.get('found_text', '').lower()
        if "debugging" in text or "android" in text:
            target = pm
            break
            
    if not target:
        # Fallback to the first proximity match if specific keywords aren't found
        target = proximity_matches[0]
        logger.info(f"Targeting first proximity match: '{target['found_text']}'")
    else:
        logger.info(f"Targeting specific match: '{target['found_text']}'")
        
    # 5. Execute Click
    logger.info(f"Clicking target at {target['box']} (Physical)...")
    
    # Scale physical to logical for pyautogui
    logical_box = [
        int(target['box'][0] / DPI_SCALE),
        int(target['box'][1] / DPI_SCALE),
        int(target['box'][2] / DPI_SCALE),
        int(target['box'][3] / DPI_SCALE)
    ]
    logger.info(f"Scaled to logical box: {logical_box}")
    
    perform_click(logical_box)
    logger.info("Click performed successfully.")
    return True

if __name__ == "__main__":
    success = verify_and_click_proximity()
    if success:
        print("SUCCESS: Proximity click executed.")
    else:
        print("FAILED: Proximity click could not be executed.")
