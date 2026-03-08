
import cv2
import numpy as np
import pyautogui
import pytesseract
import os
from PIL import Image
from contextlib import suppress
from core.config_manager import config_manager, get_resource_path
from utils.logger import logger
import pygetwindow as gw

# Known OCR misreads
OCR_ALIASES = {
    "conten": "Confirm",
    "alow": "Allow",
    "acce": "Accept",
    "expand <": "Expand",
    "expand<": "Expand",
    "expand (": "Expand",
}

# Try importing thefuzz, handle if not installed (though it should be)
try:
    from thefuzz import fuzz
except ImportError:
    logger.warning("thefuzz library not found. Fuzzy matching disabled.")
    fuzz = None

# Set Tesseract Command
tesseract_cmd = config_manager.get("TESSERACT_CMD_PATH", r'C:\Program Files\Tesseract-OCR\tesseract.exe')
if os.path.exists(tesseract_cmd):
    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
else:
    logger.warning(f"Tesseract not found at configured path: {tesseract_cmd}. Assuming it is in PATH.")



import mss

from core.exceptions import OCRError

# ...

def capture_screen(region=None):
    """Captures the screen or a specific region (x, y, w, h)."""
    try:
        with mss.mss() as sct:
            if region:
                x, y, w, h = region
                monitor = {"top": int(y), "left": int(x), "width": int(w), "height": int(h)}
                sct_img = sct.grab(monitor)
            else:
                # Grab primary monitor if no region specified
                monitor = sct.monitors[1]
                sct_img = sct.grab(monitor)
            
            # Convert to PIL Image (RGB)
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            return img
    except Exception as e:
        logger.error(f"Screen capture failed: {e}")
        # Critical error if we can't see screen
        raise OCRError(f"Screen capture failed: {e}")

# ...

def detect_blue_regions(screenshot):
    """
    Detects blue-colored regions in the screenshot using HSV color space.
    Returns a binary mask where blue regions are white (255) and others are black (0).
    """
    if not config_manager.get("ENABLE_COLOR_FILTER", True):
        return None
    
    try:
        # Convert PIL Image to OpenCV format (BGR)
        img_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        
        # Convert to HSV color space
        hsv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2HSV)
        
        # Create mask for blue color range
        lower_blue = np.array(config_manager.get("BLUE_HSV_LOWER", [100, 50, 50]))
        upper_blue = np.array(config_manager.get("BLUE_HSV_UPPER", [130, 255, 255]))
        mask = cv2.inRange(hsv, lower_blue, upper_blue)
        
        # Apply morphological operations
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        
        return mask

    except Exception as e:
        logger.error(f"Blue region detection failed: {e}")
        # Non-critical? If filter fails, we can return None to fallback to full scan?
        # But user requested error handling. Let's log and return None (soft fail) or raise?
        # Since fallback exists in scan_for_keywords, returning None is safer for app continuity.
        raise OCRError(f"Blue region detection failed: {e}")

def detect_neutral_regions(screenshot):
    """
    Detects neutral-colored regions (grey, white) in the screenshot.
    """
    if not config_manager.get("ENABLE_NEUTRAL_FILTER", False):
        return None
    
    try:
        img_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        hsv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2HSV)
        
        lower_neutral = np.array(config_manager.get("NEUTRAL_HSV_LOWER", [0, 0, 40]))
        upper_neutral = np.array(config_manager.get("NEUTRAL_HSV_UPPER", [180, 50, 200]))
        mask = cv2.inRange(hsv, lower_neutral, upper_neutral)
        
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        
        return mask
    except Exception as e:
        logger.error(f"Neutral region detection failed: {e}")
        return None

def is_on_colored_background(box, combined_mask, region_offset=(0, 0)):
    """
    Checks if a text bounding box overlaps with detected colored regions.
    """
    if combined_mask is None:
        return True
    
    try:
        x, y, w, h = box
        offset_x, offset_y = region_offset
        mask_x = x - offset_x
        mask_y = y - offset_y
        
        if mask_x < 0 or mask_y < 0: return False
        if mask_x + w > combined_mask.shape[1] or mask_y + h > combined_mask.shape[0]: return False
        
        roi = combined_mask[mask_y:mask_y + h, mask_x:mask_x + w]
        total_pixels = w * h
        if total_pixels == 0: return False
        
        colored_pixels = np.count_nonzero(roi)
        overlap_ratio = colored_pixels / total_pixels
        threshold = config_manager.get("COLOR_OVERLAP_THRESHOLD", 0.5)
        return overlap_ratio >= threshold
    except Exception as e:
        logger.error(f"Error checking colored background: {e}")
        return False

def get_target_region():
    """
    Returns the (x, y, w, h) region of the target window.
    Returns None if no target window is configured.
    Returns (0,0,0,0) if target window is configured but not found.
    """
    title = config_manager.get("TARGET_WINDOW_TITLE")
    if not title:
        return None
    
    try:
        # Partial match
        wins = gw.getWindowsWithTitle(title)
        if wins:
            # Use the first one that matches
            for w in wins:
                if title.lower() in w.title.lower():
                    return (w.left, w.top, w.width, w.height)
        logger.warning(f"Target window '{title}' not found.")
        return (0, 0, 0, 0)
    except Exception as e:
        logger.error(f"Error finding target window: {e}")
        return (0, 0, 0, 0)

def is_box_in_app_window(box, app_bounds):
    """Checks if the center of a box is within the application's own window."""
    if not app_bounds:
        return False
    
    x, y, w, h = box
    ax, ay, aw, ah = app_bounds
    
    center_x = x + w / 2
    center_y = y + h / 2
    
    return (ax <= center_x <= ax + aw) and (ay <= center_y <= ay + ah)

def scan_for_keywords(target_keywords_click, target_keywords_type):
    """
    Scans the screen (or target window) for keywords.
    Optimized: If blue filter is enabled, it scans blue regions individually for better speed.
    Returns a list of dicts: {'keyword': str, 'type': 'CLICK'|'TYPE', 'box': (x, y, w, h), 'conf': float}
    """
    region = get_target_region()
    
    # Handle case where window wasn't found - don't scan full screen if restricted
    if region == (0, 0, 0, 0):
        return []

    screenshot = capture_screen(region=region)
    print(f"DEBUG: capture_screen returned: {type(screenshot)} of size {screenshot.size if hasattr(screenshot, 'size') else 'N/A'}")
    img_np = np.array(screenshot)
    print(f"DEBUG: img_np shape: {img_np.shape}")

    
    # Region offset for coordinate mapping (0,0 if full screen)
    offset_x, offset_y = (region[0], region[1]) if region else (0, 0)
    
    # Detect regions
    enable_color = config_manager.get("ENABLE_COLOR_FILTER", True)
    enable_neutral = config_manager.get("ENABLE_NEUTRAL_FILTER", False)
    
    blue_mask = detect_blue_regions(screenshot) if enable_color else None
    neutral_mask = detect_neutral_regions(screenshot) if enable_neutral else None
    
    combined_mask = None
    if blue_mask is not None and neutral_mask is not None:
        combined_mask = cv2.bitwise_or(blue_mask, neutral_mask)
    elif blue_mask is not None:
        combined_mask = blue_mask
    elif neutral_mask is not None:
        combined_mask = neutral_mask
    
    # Get app window bounds to avoid self-clicking
    app_bounds = None
    app_title = config_manager.get("APP_TITLE")
    if app_title:
        with suppress(Exception):
            awins = gw.getWindowsWithTitle(app_title)
            if awins:
                awin = awins[0]
                awin = awins[0]
                app_bounds = (awin.left, awin.top, awin.width, awin.height)

    matches = []
    all_seen_segments = [] # List of (text, box, conf)

    if combined_mask is not None:
        # Find contours of detected regions
        contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for idx, cnt in enumerate(contours):
            x, y, w, h = cv2.boundingRect(cnt)
            # Skip noise or tiny regions - buttons are usually larger
            if w < 25 or h < 15:
                continue

            
            # Pad the region slightly for better OCR
            pad = 5
            x_pad = max(0, x - pad)
            y_pad = max(0, y - pad)
            w_pad = min(img_np.shape[1] - x_pad, w + pad * 2)
            h_pad = min(img_np.shape[0] - y_pad, h + pad * 2)
            
            crop = img_np[y_pad:y_pad+h_pad, x_pad:x_pad+w_pad]
            
            try:
                # --- Preprocessing for better OCR ---
                # 1. Grayscale
                gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
                # 2. Binarization
                # We'll try to handle both black-on-white and white-on-black by checking mean brightness
                # But typically buttons are white text on blue/dark.
                _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
                
                # 3. Upscale 3x (Better for small symbols like +)
                upscaled = cv2.resize(thresh, (0,0), fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
                
                # 4. Lightly denoise and sharpen
                upscaled = cv2.medianBlur(upscaled, 3)

                
                # Run OCR on the upscaled crop with a tiered PSM strategy
                # 1. PSM 7 (Single Line)
                config_str = '--psm 7'
                data = pytesseract.image_to_data(upscaled, config=config_str, output_type=pytesseract.Output.DICT)
                full_region_text = " ".join([t.strip() for t in data['text'] if t.strip()]).replace("|", "").strip()
                
                if not full_region_text:
                    # 2. PSM 8 (Single Word) - Often better for short button text
                    config_str = '--psm 8'
                    data = pytesseract.image_to_data(upscaled, config=config_str, output_type=pytesseract.Output.DICT)
                    full_region_text = " ".join([t.strip() for t in data['text'] if t.strip()]).replace("|", "").strip()

                if not full_region_text:
                    # 3. PSM 10 (Single Character) - Fallback for symbols like +
                    config_str = '--psm 10'
                    data = pytesseract.image_to_data(upscaled, config=config_str, output_type=pytesseract.Output.DICT)
                    full_region_text = " ".join([t.strip() for t in data['text'] if t.strip()]).replace("|", "").strip()

                # Debug: Save ALL crops
                cv2.imwrite(f"crop_{idx}.png", upscaled)

                if full_region_text:
                    logger.debug(f"DEBUG: Contour {idx} Text: '{full_region_text}' at ({x}, {y})")
                    # Use the bounding box of the entire region (not just one word)




                    # Use the bounding box of the entire region (not just one word)
                    # Use the bounding box of the entire region (not just one word)
                    full_abs_box = (offset_x + x, offset_y + y, w, h)
                    all_seen_segments.append((full_region_text, full_abs_box, 100))
                    process_text_match(full_region_text, full_region_text.lower(), 100, full_abs_box, 
                                       target_keywords_click, target_keywords_type, matches, app_bounds)

            except Exception as e:
                logger.error(f"OCR Failed on region: {e}")
                continue

            n_boxes = len(data['text'])
            for i in range(n_boxes):
                text = data['text'][i].strip()
                conf = int(data['conf'][i])
                
                if not text or conf < config_manager.get("OCR_CONFIDENCE_THRESHOLD", 60):
                    continue
                
                text_lower = text.lower()
                
                # Calculate ABSOLUTE screen coordinates
                # Adjusted for 3x upscale: data['left'][i] / 3
                abs_x = offset_x + x_pad + (data['left'][i] // 3)
                abs_y = offset_y + y_pad + (data['top'][i] // 3)
                abs_w = data['width'][i] // 3
                abs_h = data['height'][i] // 3

                abs_box = (abs_x, abs_y, abs_w, abs_h)
                all_seen_segments.append((text, abs_box, conf))
                # Check keywords
                process_text_match(text, text_lower, conf, abs_box, target_keywords_click, target_keywords_type, matches, app_bounds)

    else:
        # Fallback to full screen scan if color filter disabled or failed
        logger.debug("Falling back to full screenshot OCR scan...")
        try:
            data = pytesseract.image_to_data(screenshot, output_type=pytesseract.Output.DICT)
        except Exception as e:
            logger.error(f"OCR Failed: {e}")
            return []

        n_boxes = len(data['text'])
        for i in range(n_boxes):
            text = data['text'][i].strip()
            conf = int(data['conf'][i])
            
            if not text or conf < config_manager.get("OCR_CONFIDENCE_THRESHOLD", 60):
                continue
            
            text_lower = text.lower()
            abs_x = offset_x + data['left'][i]
            abs_y = offset_y + data['top'][i]
            abs_w = data['width'][i]
            abs_h = data['height'][i]
            abs_box = (abs_x, abs_y, abs_w, abs_h)
            all_seen_segments.append((text, abs_box, conf))
            
            process_text_match(text, text_lower, conf, abs_box, target_keywords_click, target_keywords_type, matches, app_bounds)


    # --- Template Matching ---
    template_paths = config_manager.get("TEMPLATES", [])
    threshold = config_manager.get("TEMPLATE_MATCHING_THRESHOLD", 0.8)
    
    if template_paths:
        for t_path in template_paths:
            abs_t_path = get_resource_path(t_path)
            if not os.path.exists(abs_t_path):
                logger.warning(f"Template not found: {abs_t_path}")
                continue
                
            template = cv2.imread(abs_t_path)
            if template is None: continue
            
            # Match template
            res = cv2.matchTemplate(img_np, template, cv2.TM_CCOEFF_NORMED)
            locs = np.where(res >= threshold)
            
            t_h, t_w = template.shape[:2]
            for pt in zip(*locs[::-1]): # Switch x and y
                # Filter duplicates (e.g. within 10px)
                is_dup = False
                for m in matches:
                    if m['type'] == 'CLICK' and abs(m['box'][0] - (offset_x + pt[0])) < 10 and abs(m['box'][1] - (offset_y + pt[1])) < 10:
                        is_dup = True
                        break
                if is_dup: continue
                
                abs_box = (offset_x + pt[0], offset_y + pt[1], t_w, t_h)
                
                # Safety check
                if app_bounds and is_box_in_app_window(abs_box, app_bounds):
                    continue
                
                matches.append({
                    'keyword': os.path.basename(t_path),
                    'found_text': f"Template: {os.path.basename(t_path)}",
                    'type': 'CLICK',
                    'box': abs_box,
                    'conf': float(res[pt[1], pt[0]]) * 100
                })
                logger.info(f"Found template match: {t_path} at {abs_box}")

    # --- Proximity Matching ---
    if config_manager.get("PROXIMITY_CLICKING_ENABLED", False):
        _add_proximity_matches(matches, all_seen_segments)

    return matches

def _add_proximity_matches(matches, all_segments):
    """Adds matches for text near anchor keywords/templates."""
    anchors = config_manager.get("ANCHOR_KEYWORDS", ["El", "Bell", "bell_icon.png"])
    max_dist = config_manager.get("PROXIMITY_MAX_DISTANCE", 300)
    direction = config_manager.get("PROXIMITY_DIRECTION", "BOTH").upper()
    
    current_matches = list(matches) # Avoid modifying while iterating
    
    for m in current_matches:
        # Check if any anchor is a partial match to the keyword or found text
        is_anchor = False
        for a in anchors:
            if fuzz:
                if fuzz.partial_ratio(a.lower(), m['keyword'].lower()) >= 90:
                    is_anchor = True
                    break
            elif a.lower() in m['keyword'].lower():
                is_anchor = True
                break
        
        if is_anchor:
            ax, ay, aw, ah = m['box']
            ac_y = ay + ah/2
            
            for text, box, conf in all_segments:
                tx, ty, tw, th = box
                tc_y = ty + th/2
                
                # Check if it's the same box
                if tx == ax and ty == ay: continue
                
                # Vertical overlap check (same line)
                if abs(ac_y - tc_y) > (ah + th) / 2: continue
                
                # Horizontal distance check and direction filter
                dist = -1
                is_right = tx > (ax + aw)
                is_left = (tx + tw) < ax
                
                if direction == "LEFT":
                    if is_left:
                        dist = ax - (tx + tw)
                elif direction == "RIGHT":
                    if is_right:
                        dist = tx - (ax + aw)
                else: # BOTH or unspecified
                    if is_right:
                        dist = tx - (ax + aw)
                    elif is_left:
                        dist = ax - (tx + tw)
                    else: # Overlapping or inside
                        dist = 0
                
                if dist >= 0 and dist < max_dist:
                    # Avoid duplicates
                    is_dup = False
                    for existing in matches:
                        if existing['box'] == box:
                            is_dup = True
                            break
                    if is_dup: continue
                    
                    matches.append({
                        'keyword': f"Proximity({m['keyword']})",
                        'found_text': text,
                        'type': 'CLICK',
                        'box': box,
                        'conf': conf
                    })
                    logger.info(f"Proximity Match: Found '{text}' near '{m['keyword']}' ({direction}) at {box}")

def process_text_match(text, text_lower, conf, abs_box, target_keywords_click, target_keywords_type, matches, app_bounds=None):
    """Refactored matching logic used by both scan paths."""
    # Safety: check if this coordinate is within our own app window
    if app_bounds and is_box_in_app_window(abs_box, app_bounds):
        # logger.debug(f"Ignoring keyword '{text}' as it is within the app's own window.")
        return matches

    # Apply aliases
    if text_lower in OCR_ALIASES:
        logger.debug(f"Aliasing '{text}' -> '{OCR_ALIASES[text_lower]}'")
        text = OCR_ALIASES[text_lower]
        text_lower = text.lower()
    
    # Check CLICK keywords
    for k in target_keywords_click:
        match_found = False
        if fuzz:
            # Use partial_ratio so that keywords like "Expand" match OCR reads like "Expand <"
            ratio = fuzz.partial_ratio(text_lower, k.lower())
            # For symbols like '+', exact contains check might be safer
            if k in ['+', '-'] and k in text_lower:
                match_found = True
            elif ratio >= 90: # partial_ratio is more lenient; use >= 90 to stay accurate
                match_found = True
        elif text_lower == k.lower() or (k in ['+', '-'] and k in text_lower):
            match_found = True

        if match_found:
            matches.append({
                'keyword': k,
                'found_text': text,
                'type': 'CLICK',
                'box': abs_box,
                'conf': conf
            })
            logger.debug(f"Found '{k}' (text='{text}') at {abs_box}")

    
    # Check TYPE keywords
    for k in target_keywords_type:
        match_found = False
        if fuzz:
            ratio = fuzz.ratio(text_lower, k.lower())
            if ratio > 90:
                match_found = True
        elif text_lower == k.lower():
            match_found = True
        
        if match_found:
            matches.append({
                'keyword': k,
                'found_text': text,
                'type': 'TYPE',
                'box': abs_box,
                'conf': conf
            })
            logger.debug(f"Found '{k}' (text='{text}') at {abs_box}")

    return matches

