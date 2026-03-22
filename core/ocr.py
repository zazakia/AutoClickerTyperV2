import cv2
import numpy as np
import pyautogui
import pytesseract
import os
from PIL import Image
from contextlib import suppress
import concurrent.futures
from core.config_manager import config_manager, get_resource_path
from utils.logger import logger
import pygetwindow as gw

# DPI Awareness for Windows
if os.name == 'nt':
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception as e:
        print(f"Failed to set DPI awareness: {e}")

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

def get_color_masks(screenshot):
    """
    Detects regions based on configured color profiles.
    Returns a dictionary of mask arrays keyed by profile name.
    """
    if not config_manager.get("ENABLE_COLOR_FILTER", True):
        return None
    
    try:
        img_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        hsv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2HSV)
        
        profiles = config_manager.get("BUTTON_COLOR_PROFILES", [])
        if not profiles:
            return None
            
        masks = {}
        kernel = np.ones((5, 5), np.uint8)
        
        # Flexibility for formats
        if isinstance(profiles, list):
            for p in profiles:
                try:
                    name = p.get("name", "unknown")
                    lower = np.array(p.get("lower", p.get("low", [0, 0, 0])))
                    upper = np.array(p.get("upper", p.get("high", [180, 255, 255])))
                    mask = cv2.inRange(hsv, lower, upper)
                    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
                    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel) # Added this line back from original
                    masks[name] = mask
                except Exception as e:
                    logger.warning(f"Skipping malformed profile {p}: {e}")
        elif isinstance(profiles, dict):
            for name, p in profiles.items():
                try:
                    lower = np.array(p.get("low", p.get("lower", [0, 0, 0])))
                    upper = np.array(p.get("high", p.get("upper", [180, 255, 255])))
                    mask = cv2.inRange(hsv, lower, upper)
                    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
                    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel) # Added this line back from original
                    masks[name] = mask
                except Exception as e:
                    logger.warning(f"Skipping malformed profile {name}: {e}")
        
        return masks if masks else None
    except Exception as e:
        logger.error(f"Color mask generation failed: {e}")
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
    import re
    title_pattern = config_manager.get("TARGET_WINDOW_REGEX", "")
    title = config_manager.get("TARGET_WINDOW_TITLE", "")
    
    if not title_pattern and not title:
        return None
    
    try:
        if title_pattern:
            all_wins = gw.getAllWindows()
            candidates = [w for w in all_wins if re.search(title_pattern, w.title, re.IGNORECASE)]
            logger.info(f"Found {len(candidates)} windows matching regex '{title_pattern}'")
        else:
            wins = gw.getWindowsWithTitle(title)
            candidates = [w for w in wins if title.lower() in w.title.lower()]
            logger.info(f"Found {len(candidates)} windows partially matching '{title}'")
        
        if candidates:
            # Prefer exact title match first if not using regex
            if not title_pattern:
                exact = [w for w in candidates if w.title == title]
                if exact:
                    candidates = exact

            # Prefer the one that is visible and not at 0,0
            best = candidates[0]
            for c in candidates:
                if c.visible and (c.left != 0 or c.top != 0) and c.title != "Program Manager":
                    best = c
                    break
            
            logger.info(f"Selected match: '{best.title}' at {best.left}, {best.top} ({best.width}x{best.height})")
            return (best.left, best.top, best.width, best.height)

        logger.warning(f"Target window matching '{title_pattern or title}' not found.")
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

def scan_for_keywords(target_keywords_click, target_keywords_type, override_region=None, debug_segments=False):
    """
    Scans the screen (or target window) for keywords.
    Optimized: If blue filter is enabled, it scans blue regions individually for better speed.
    Returns a list of dicts: {'keyword': str, 'type': 'CLICK'|'TYPE', 'box': (x, y, w, h), 'conf': float}
    """
    region = override_region if override_region else get_target_region()
    
    # Handle case where window wasn't found - don't scan full screen if restricted
    if region == (0, 0, 0, 0):
        return []

    screenshot = capture_screen(region=region)
    logger.debug(f"capture_screen returned: {type(screenshot)} of size {screenshot.size if hasattr(screenshot, 'size') else 'N/A'}")
    img_np = np.array(screenshot)
    logger.debug(f"img_np shape: {img_np.shape}")

    
    # Region offset for coordinate mapping (0,0 if full screen)
    offset_x, offset_y = (region[0], region[1]) if region else (0, 0)
    
    # Detect regions
    color_masks = get_color_masks(screenshot)
    combined_mask = None
    if color_masks:
        for m in color_masks.values():
            if combined_mask is None:
                combined_mask = m
            else:
                combined_mask = cv2.bitwise_or(combined_mask, m)

    
    # Get app window bounds to avoid self-clicking
    app_bounds = None
    app_title = config_manager.get("APP_TITLE")
    if app_title:
        with suppress(Exception):
            awins = gw.getWindowsWithTitle(app_title)
            if awins:
                awin = awins[0]
                app_bounds = (awin.left, awin.top, awin.width, awin.height)

    matches = []
    all_seen_segments = [] # List of (text, box, conf)

    if combined_mask is not None:
        # Find contours of detected regions
        contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        def process_contour(cnt, idx):
            local_segments = []
            local_matches = []
            x, y, w, h = cv2.boundingRect(cnt)
            # Skip noise or tiny regions
            if w < 10 or h < 10:
                return local_segments, local_matches

            # Determine dominant color profile for this contour
            # This is optional optimization, for now we just use the combined mask
            
            # Pad the region slightly for better OCR
            pad = 5
            x_pad = max(0, x - pad)
            y_pad = max(0, y - pad)
            w_pad = min(img_np.shape[1] - x_pad, w + pad * 2)
            h_pad = min(img_np.shape[0] - y_pad, h + pad * 2)
            
            crop = img_np[y_pad:y_pad+h_pad, x_pad:x_pad+w_pad]
            
            try:
                # --- Preprocessing for better OCR ---
                gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
                enhanced = clahe.apply(gray)

                _, thresh_inv = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
                _, thresh_std = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                
                thresh = thresh_inv
                if np.mean(enhanced) > 127:
                    thresh = thresh_std
                else:
                    thresh = thresh_inv

                upscaled = cv2.resize(thresh, (0,0), fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
                upscaled = cv2.medianBlur(upscaled, 3)

                # Smarter PSM Selection based on aspect ratio
                aspect_ratio = w / h
                if aspect_ratio >= 3.0:
                    config_str = '--psm 7' # Single line
                elif aspect_ratio >= 1.0:
                    config_str = '--psm 8' # Single word
                else:
                    config_str = '--psm 10' # Single char/symbol
                
                data = pytesseract.image_to_data(upscaled, config=config_str, output_type=pytesseract.Output.DICT)
                full_region_text = " ".join([t.strip() for t in data['text'] if t.strip()]).replace("|", "").strip()
                
                if not full_region_text and aspect_ratio >= 1.0:
                    # Fallback to single char if it was a square-ish thing that failed
                    data = pytesseract.image_to_data(upscaled, config='--psm 10', output_type=pytesseract.Output.DICT)
                    full_region_text = " ".join([t.strip() for t in data['text'] if t.strip()]).replace("|", "").strip()

                if config_manager.get("DEBUG_MODE", False):
                    cv2.imwrite(f"crop_{idx}.png", upscaled)

                if full_region_text:
                    logger.debug(f"Contour {idx} Text: '{full_region_text}' at ({x}, {y})")
                    full_abs_box = (offset_x + x, offset_y + y, w, h)
                    local_segments.append((full_region_text, full_abs_box, 100))
                    # Check keyword to color profile logic
                    process_text_match(full_region_text, full_region_text.lower(), 100, full_abs_box, 
                                       target_keywords_click, target_keywords_type, local_matches, app_bounds)

            except Exception as e:
                logger.error(f"OCR Failed on region: {e}")

            # Also check individual words from data
            if 'data' in locals():
                n_boxes = len(data['text'])
                for i in range(n_boxes):
                    text = data['text'][i].strip()
                    conf = int(data['conf'][i])
                    
                    if not text or conf < config_manager.get("OCR_CONFIDENCE_THRESHOLD", 60):
                        continue
                    
                    text_lower = text.lower()
                    abs_x = offset_x + x_pad + (data['left'][i] // 3)
                    abs_y = offset_y + y_pad + (data['top'][i] // 3)
                    abs_w = data['width'][i] // 3
                    abs_h = data['height'][i] // 3

                    abs_box = (abs_x, abs_y, abs_w, abs_h)
                    local_segments.append((text, abs_box, conf))
                    
                    # Prevent duplicates if it matched full region
                    is_dup = any(m['box'] == abs_box and m['keyword'].lower() in text_lower for m in local_matches)
                    if not is_dup:
                        process_text_match(text, text_lower, conf, abs_box, target_keywords_click, target_keywords_type, local_matches, app_bounds)
                        
            return local_segments, local_matches

        max_workers = config_manager.get("SCAN_PARALLELISM", 4)
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(process_contour, cnt, idx) for idx, cnt in enumerate(contours)]
            for future in concurrent.futures.as_completed(futures):
                try:
                    loc_segs, loc_matches = future.result()
                    all_seen_segments.extend(loc_segs)
                    matches.extend(loc_matches)
                except Exception as e:
                    logger.error(f"Parallel processing error: {e}")

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

    # --- Motion Detection (Animated Targets) ---
    if config_manager.get("MOTION_DETECTION_ENABLED", True):
        motion_matches = detect_motion(region)
        matches.extend(motion_matches)

    if debug_segments:
        return matches, all_seen_segments
    return matches

def _add_proximity_matches(matches, all_segments):
    """Adds matches for text near anchor keywords/templates using optimized spatial grouping."""
    anchors_cfg = config_manager.get("ANCHOR_KEYWORDS", ["El", "Bell", "bell_icon.png"])
    max_dist = config_manager.get("PROXIMITY_MAX_DISTANCE", 300)
    direction = config_manager.get("PROXIMITY_DIRECTION", "BOTH").upper()
    
    if not all_segments:
        return

    # 1. Identify all anchors first
    anchor_boxes = []
    for text, box, conf in all_segments:
        is_anchor = False
        text_lower = text.lower()
        for a in anchors_cfg:
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
            anchor_boxes.append((text, box, conf))

    if not anchor_boxes:
        return

    # 2. Group all segments by Y-coordinate (using a small margin for "same line")
    # Margin is roughly the average height of a segment, or a fixed value like 15px
    line_map = {}
    for text, box, conf in all_segments:
        x, y, w, h = box
        center_y = y + h / 2
        line_key = int(center_y // 15) # Group into 15px vertical buckets
        for k in range(line_key - 1, line_key + 2): # Check adjacent buckets too
            if k not in line_map: line_map[k] = []
            line_map[k].append((text, box, conf))

    # 3. For each anchor, only check segments in the same or adjacent Y-buckets
    for a_text, a_box, a_conf in anchor_boxes:
        logger.debug(f"Anchor found: '{a_text}' at {a_box}")
        ax, ay, aw, ah = a_box
        ac_y = ay + ah / 2
        line_key = int(ac_y // 15)
        
        # Get candidates from relevant buckets
        candidates = line_map.get(line_key, [])
        
        for t_text, t_box, t_conf in candidates:
            tx, ty, tw, th = t_box
            tc_y = ty + th / 2
            
            # Skip if same box
            if tx == ax and ty == ay: continue
            
            # Double check vertical overlap (same line)
            y_diff = abs(ac_y - tc_y)
            if y_diff > (ah + th): continue 
            
            # Horizontal distance check
            dist = -1
            is_right = tx > (ax + aw / 2)
            is_left = (tx + tw) < (ax + aw / 2)
            
            if direction == "LEFT":
                if is_left: dist = ax - (tx + tw)
            elif direction == "RIGHT":
                if is_right: dist = tx - (ax + aw)
            else: # BOTH
                if is_right: dist = tx - (ax + aw)
                elif is_left: dist = ax - (tx + tw)
                else: dist = 0
            
            if 0 <= dist < max_dist:
                # Avoid duplicates
                is_dup = any(existing['box'] == t_box and existing['keyword'] == f"Proximity({a_text})" for existing in matches)
                if is_dup: continue
                
                matches.append({
                    'keyword': f"Proximity({a_text})",
                    'found_text': t_text,
                    'type': 'CLICK',
                    'box': t_box,
                    'conf': t_conf
                })
                logger.info(f"Proximity Match: '{t_text}' near '{a_text}' at {t_box}")

def detect_motion(region=None):
    """
    Detects moving/animated elements (like a spinning 'C' icon).
    Captures two frames closely in time and computes the absolute difference.
    """
    try:
        # Capture first frame
        frame1 = np.array(capture_screen(region=region))
        frame1_gray = cv2.cvtColor(frame1, cv2.COLOR_RGB2GRAY)
        
        # Wait a tiny bit (enough for an animation frame to change)
        import time
        time.sleep(0.1)
        
        # Capture second frame
        frame2 = np.array(capture_screen(region=region))
        frame2_gray = cv2.cvtColor(frame2, cv2.COLOR_RGB2GRAY)
        
        # Compute absolute difference
        diff = cv2.absdiff(frame1_gray, frame2_gray)
        
        # Threshold to get significant differences
        _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
        
        # Dilate to connect broken parts of the animation
        kernel = np.ones((5,5), np.uint8)
        dilated = cv2.dilate(thresh, kernel, iterations=2)
        
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        motion_matches = []
        offset_x, offset_y = (region[0], region[1]) if region else (0, 0)
        
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            area = w * h
            
            # Filter objects: spinning C indicator is usually small/medium, square-ish
            # Avoid full screen scrolls (huge area) or tiny blinkers (small area)
            min_area = config_manager.get("MOTION_MIN_AREA", 100)
            max_area = config_manager.get("MOTION_MAX_AREA", 5000)
            
            if min_area < area < max_area:
                aspect_ratio = float(w) / h if h != 0 else 0
                if 0.5 < aspect_ratio < 2.0: # Roughly square
                    abs_box = (offset_x + x, offset_y + y, w, h)
                    motion_matches.append({
                        'keyword': 'MotionDetected(C_Icon)',
                        'found_text': 'Animated Element',
                        'type': 'CLICK',
                        'box': abs_box,
                        'conf': 100.0  # Confident it moved
                    })
                    logger.info(f"Motion detected at {abs_box}")
                    
        return motion_matches

    except Exception as e:
        logger.error(f"Motion detection failed: {e}")
        return []

def detect_scrollbars(region=None):
    """
    Finds scrollbar thumbs using templates.
    """
    try:
        screenshot = capture_screen(region=region)
        img_np = np.array(screenshot)
        
        template_name = "scrollbar_thumb.png"
        abs_t_path = get_resource_path(f"templates/{template_name}")
        
        if not os.path.exists(abs_t_path):
            logger.debug(f"Scrollbar template not found at {abs_t_path}. Ensure it is saved.")
            return []
            
        template = cv2.imread(abs_t_path)
        if template is None: return []
        
        res = cv2.matchTemplate(img_np, template, cv2.TM_CCOEFF_NORMED)
        threshold = config_manager.get("SCROLLBAR_MATCH_THRESHOLD", 0.7)
        locs = np.where(res >= threshold)
        
        t_h, t_w = template.shape[:2]
        offset_x, offset_y = (region[0], region[1]) if region else (0, 0)
        
        scrollbars = []
        for pt in zip(*locs[::-1]):
            # Filter duplicates (very close matches)
            abs_box = (offset_x + pt[0], offset_y + pt[1], t_w, t_h)
            is_dup = False
            for s in scrollbars:
                if abs(s[0] - abs_box[0]) < 10 and abs(s[1] - abs_box[1]) < 10:
                    is_dup = True
                    break
            if not is_dup:
                scrollbars.append(abs_box)
                
        return scrollbars
        
    except Exception as e:
        logger.error(f"Scrollbar detection failed: {e}")
        return []

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

