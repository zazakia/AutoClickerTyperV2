import time
import sys
import os
from core.config_manager import config_manager
from core.ocr import scan_for_keywords
from core.actions import perform_click
from utils.logger import logger

def verify_and_click_proximity():
    logger.info("Starting Proximity Click Verification...")
    
    # 1. Configuration
    config_manager.set("TARGET_WINDOW_TITLE", "Manager")
    config_manager.set("PROXIMITY_CLICKING_ENABLED", True)
    config_manager.set("PROXIMITY_DIRECTION", "LEFT")
    config_manager.set("ANCHOR_KEYWORDS", ["Bell", "bell", "El", "ll"])
    config_manager.set("CLICK_KEYWORDS", ["Accept", "Allow", "Proceed", "Confirm", "Expand", "Bell", "bell", "El", "ll"])
    
    logger.info("Scanning for bell anchor and proximity matches...")
    
    # 2. Scan
    # We pass empty type_keywords to focus only on search/click
    matches = scan_for_keywords(config_manager.get("CLICK_KEYWORDS"), [])
    
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
    logger.info(f"Clicking target at {target['box']}...")
    perform_click(target['box'])
    logger.info("Click performed successfully.")
    return True

if __name__ == "__main__":
    success = verify_and_click_proximity()
    if success:
        print("SUCCESS: Proximity click executed.")
    else:
        print("FAILED: Proximity click could not be executed.")
