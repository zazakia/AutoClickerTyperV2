import time
from core.ocr import scan_for_keywords
from core.config_manager import config_manager
from utils.logger import logger
from core.exceptions import OCRError

def verify_action(expected_keyword, original_box, timeout=1.0):
    """
    Verifies that the action succeeded by checking if the specific button 
    at the original location is GONE. Timeout reduced to 1.0s.
    Uses targeted region scan for speed and precision.
    """
    start_time = time.time()
    
    # Calculate targeted region: original box + 50px padding on all sides
    ox, oy, ow, oh = original_box
    target_region = (
        max(0, ox - 50), 
        max(0, oy - 50), 
        ow + 100, 
        oh + 100
    )
    
    while time.time() - start_time < timeout:
        try:
            # Targeted scan only in the sub-region where the button was
            matches = scan_for_keywords(
                config_manager.get("CLICK_KEYWORDS", []), 
                config_manager.get("TYPE_KEYWORDS", []),
                override_region=target_region
            )
            
            # Check for overlap with original_box in the new matches
            still_present = False
            for m in matches:
                if m['keyword'] == expected_keyword:
                    # check overlap with original coordinates
                    if boxes_overlap(original_box, m['box']):
                        still_present = True
                        break
            
            if not still_present:
                msg = f"Verification Success: '{expected_keyword}' is gone."
                logger.info(msg)
                return True, msg
                
        except OCRError as e:
            logger.warning(f"Verification scan failed (OCRError): {e}. Ignoring this frame.")
        except Exception as e:
            logger.warning(f"Verification error: {e}")

        time.sleep(0.2) # Faster polling for targeted scan
        
    msg = f"Verification Warning: '{expected_keyword}' still detected at original location."
    logger.warning(msg)
    return False, msg

def boxes_overlap(box1, box2, threshold=0.5):
    """Checks if two boxes overlap significantly."""
    try:
        x1, y1, w1, h1 = box1
        x2, y2, w2, h2 = box2
        
        # Intersection
        xi1 = max(x1, x2)
        yi1 = max(y1, y2)
        xi2 = min(x1+w1, x2+w2)
        yi2 = min(y1+h1, y2+h2)
        
        inter_area = max(0, xi2 - xi1) * max(0, yi2 - yi1)
        if inter_area == 0: return False
        
        # Area of smallest box
        area1 = w1 * h1
        area2 = w2 * h2
        min_area = min(area1, area2)
        
        return (inter_area / min_area) > threshold
    except Exception:
        return False
