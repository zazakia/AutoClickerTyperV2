
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
    "expand [": "Expand",
    "expand{": "Expand",
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
        wins = gw.getWindowsWithTitle(title)
        logger.info(f"Found {len(wins)} windows matching '{title}'")
        
        candidates = []
        for i, w in enumerate(wins):
            logger.info(f"  Candidate {i}: '{w.title}' at {w.left}, {w.top}, {w.width}x{w.height} Visible={w.visible}")
            if w.title == title:
                candidates.append(w)
        
        if candidates:
            # Prefer the one that is visible and not at 0,0 if multiple
            best = candidates[0]
            for c in candidates:
                if c.visible and (c.left != 0 or c.top != 0):
                    best = c
                    break
            logger.info(f"Selected Best Match: '{best.title}' at {best.left}, {best.top}")
            return (best.left, best.top, best.width, best.height)
        
        # Fallback to partial if no exact
        for w in wins:
            if title.lower() in w.title.lower() and w.title != "Program Manager":
                logger.info(f"Selected Partial Match: '{w.title}' at {w.left}, {w.top}")
                return (w.left, w.top, w.width, w.height)

        logger.warning(f"Target window '{title}' not found.")
        return None
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

def scan_for_keywords(target_keywords_click, target_keywords_type, debug_segments=False):
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
            if w < 10 or h < 10:
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
            
            # Efficiently collect best matches using non-max suppression principle
            found_locs = []
            for pt in zip(*locs[::-1]):
                abs_box = (offset_x + pt[0], offset_y + pt[1], t_w, t_h)
                
                # Check for existing template matches in this region
                is_dup = False
                for fx, fy, fw, fh, fs in found_locs:
                    if abs(fx - abs_box[0]) < t_w and abs(fy - abs_box[1]) < t_h:
                        is_dup = True
                        break
                if is_dup: continue
                
                # Safety check for app window
                if app_bounds and is_box_in_app_window(abs_box, app_bounds):
                    continue
                
                score = float(res[pt[1], pt[0]]) * 100
                found_locs.append((*abs_box, score))
                
                matches.append({
                    'keyword': os.path.basename(t_path),
                    'found_text': f"Template: {os.path.basename(t_path)}",
                    'type': 'CLICK',
                    'box': abs_box,
                    'conf': score
                })
                logger.info(f"Found template match: {t_path} at {abs_box} (Score: {score:.1f})")

    # --- Proximity Matching ---
    if config_manager.get("PROXIMITY_CLICKING_ENABLED", False):
        _add_proximity_matches(matches, all_seen_segments)

    if debug_segments:
        return matches, all_seen_segments
    return matches

def _add_proximity_matches(matches, all_segments):
    """Adds matches for text near anchor keywords/templates."""
    anchors = config_manager.get("ANCHOR_KEYWORDS", ["El", "Bell", "bell_icon.png"])
    max_dist = config_manager.get("PROXIMITY_MAX_DISTANCE", 300)
    direction = config_manager.get("PROXIMITY_DIRECTION", "BOTH").upper()
    
    # We want to find anchors within all_segments, not just the pre-matched matches
    # This ensures we find proximity targets even if the anchor itself wasn't "clicked"
    for text, box, conf in all_segments:
        is_anchor = False
        text_lower = text.lower()
        for a in anchors:
            a_lower = a.lower()
            if text_lower == a_lower:
                is_anchor = True
                break
            if fuzz and len(text_lower) > 1 and len(a_lower) > 1:
                if fuzz.partial_ratio(a_lower, text_lower) >= 90:
                    is_anchor = True
                    break
            elif len(a_lower) > 2 and a_lower in text_lower:
                is_anchor = True
                break
        
        if is_anchor:
            logger.debug(f"Potential Anchor Found: '{text}' at {box}")
            ax, ay, aw, ah = box
            ac_y = ay + ah/2
            
            for t_text, t_box, t_conf in all_segments:
                tx, ty, tw, th = t_box
                tc_y = ty + th/2
                
                # Check if it's the same box
                if tx == ax and ty == ay: continue
                
                # Vertical overlap check (same line)
                y_diff = abs(ac_y - tc_y)
                if y_diff > (ah + th): continue 
                
                # Horizontal distance check and direction filter
                dist = -1
                is_right = tx > (ax + aw / 2) # Center-based check
                is_left = (tx + tw) < (ax + aw / 2)
                
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
                
                if dist >= 0:
                    logger.debug(f"  Proximity candidate: '{t_text}' dist={dist} direction_match={dist < max_dist}")
                
                if dist >= 0 and dist < max_dist:
                    # Avoid duplicates
                    is_dup = False
                    for existing in matches:
                        if existing['box'] == t_box and existing['keyword'] == f"Proximity({text})":
                            is_dup = True
                            break
                    if is_dup: continue
                    
                    matches.append({
                        'keyword': f"Proximity({text})",
                        'found_text': t_text,
                        'type': 'CLICK',
                        'box': t_box,
                        'conf': t_conf
                    })
                    logger.info(f"Proximity Match: Found '{t_text}' near '{text}' ({direction}) at {t_box}")

def process_text_match(text, text_lower, conf, abs_box, target_keywords_click, target_keywords_type, matches, app_bounds=None):
    """Refactored matching logic used by both scan paths."""
    # Safety: check if this coordinate is within our own app window
    if app_bounds and is_box_in_app_window(abs_box, app_bounds):
        return matches

    # Apply aliases
    if text_lower in OCR_ALIASES:
        logger.debug(f"Aliasing '{text}' -> '{OCR_ALIASES[text_lower]}'")
        text = OCR_ALIASES[text_lower]
        text_lower = text.lower()
    
    # Check CLICK keywords
    for k in target_keywords_click:
        k_lower = k.lower()
        match_found = False
        match_score = conf # Default score is current confidence
        
        # Exact match first
        if text_lower == k_lower:
            match_found = True
            match_score = conf * 1.0 # Perfect match
        elif k in ['+', '-'] and k in text_lower:
            match_found = True
            match_score = conf * 1.0
        elif fuzz and len(text_lower) >= 2 and len(k_lower) >= 2:
            # Use partial_ratio to handle things like "Expand <" matching "Expand"
            p_ratio = fuzz.partial_ratio(text_lower, k_lower)
            # Use full ratio to weight the confidence
            f_ratio = fuzz.ratio(text_lower, k_lower)
            
            # Substring protection: if keyword is much longer than found text, skip
            # e.g. "and" shouldn't match "expand" with high confidence
            if len(k_lower) > len(text_lower) + 3:
                continue

            if p_ratio >= 98: 
                match_found = True
                # Weight confidence by how well it matches overall
                match_score = conf * (f_ratio / 100.0)
                # Ensure it doesn't drop too low for partial matches that are actually good
                if p_ratio == 100:
                    match_score = max(match_score, conf * 0.9)
        elif k_lower in text_lower and len(k_lower) > 3:
            if len(k_lower) > len(text_lower) + 3: continue
            match_found = True
            match_score = conf * 0.8 # Lower score for simple contains

        if match_found:
            matches.append({
                'keyword': k,
                'found_text': text,
                'type': 'CLICK',
                'box': abs_box,
                'conf': match_score
            })
            logger.debug(f"Found '{k}' (text='{text}') at {abs_box} | Weighted Conf: {match_score:.1f}")

    # Check TYPE keywords
    for k in target_keywords_type:
        k_lower = k.lower()
        match_found = False
        if fuzz:
            ratio = fuzz.ratio(text_lower, k_lower)
            if ratio > 90:
                match_found = True
        elif text_lower == k_lower:
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

