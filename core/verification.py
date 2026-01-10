import time
from core.ocr import scan_for_keywords
from utils.logger import logger
import config

def verify_action(target_keyword, action_type, target_box):
    """
    Verifies if the action was successful by checking if the keyword 
    is gone from the specific target region.
    """
    time.sleep(1.0) # Wait for UI to update
    
    # Re-scan
    matches = scan_for_keywords([target_keyword] if action_type == 'CLICK' else [], 
                                [target_keyword] if action_type == 'TYPE' else [])
    
    # Check if any match matches the original box (overlap)
    tx, ty, tw, th = target_box
    
    for m in matches:
        if m['keyword'] == target_keyword:
            mx, my, mw, mh = m['box']
            
            # Check intersection
            x_left = max(tx, mx)
            y_top = max(ty, my)
            x_right = min(tx + tw, mx + mw)
            y_bottom = min(ty + th, my + mh)
            
            if x_right > x_left and y_bottom > y_top:
                # They overlap
                overlap_area = (x_right - x_left) * (y_bottom - y_top)
                # If overlap is significant (e.g. > 10% of original area, or just > 0)
                # Let's say any significant overlap implies it's the same object
                if overlap_area > 0:
                     return False, f"Keyword '{target_keyword}' still present at target location (Overlap)"

    return True, "Keyword disappeared from target location"
