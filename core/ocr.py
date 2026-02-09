import cv2
import numpy as np
import pyautogui
import pytesseract
import os
from PIL import Image
from contextlib import suppress
from core.config_manager import config_manager
from utils.logger import logger
import pygetwindow as gw

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
        
        # Apply morphological operations to reduce noise
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

def is_on_blue_background(box, blue_mask, region_offset=(0, 0)):
    """
    Checks if a text bounding box overlaps with blue regions.
    
    Args:
        box: (x, y, w, h) - absolute screen coordinates of text
        blue_mask: Binary mask of blue regions
        region_offset: (offset_x, offset_y) - offset if scanning a window region
    
    Returns:
        True if the text box has sufficient overlap with blue regions
    """
    if blue_mask is None:
        return True  # If color filtering is disabled, allow all
    
    try:
        x, y, w, h = box
        offset_x, offset_y = region_offset
        
        # Convert absolute coordinates to mask coordinates
        mask_x = x - offset_x
        mask_y = y - offset_y
        
        # Ensure coordinates are within mask bounds
        if mask_x < 0 or mask_y < 0:
            return False
        if mask_x + w > blue_mask.shape[1] or mask_y + h > blue_mask.shape[0]:
            return False
        
        # Extract the region of interest from the mask
        roi = blue_mask[mask_y:mask_y + h, mask_x:mask_x + w]
        
        # Calculate the percentage of blue pixels in the ROI
        total_pixels = w * h
        if total_pixels == 0:
            return False
        
        blue_pixels = np.count_nonzero(roi)
        overlap_ratio = blue_pixels / total_pixels
        
        # Check if overlap meets threshold
        threshold = config_manager.get("COLOR_OVERLAP_THRESHOLD", 0.5)
        return overlap_ratio >= threshold
    except Exception as e:
        logger.error(f"Error checking blue background: {e}")
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
    img_np = np.array(screenshot)
    
    # Region offset for coordinate mapping (0,0 if full screen)
    offset_x, offset_y = (region[0], region[1]) if region else (0, 0)
    
    # Detect blue regions if color filtering is enabled
    enable_color = config_manager.get("ENABLE_COLOR_FILTER", True)
    blue_mask = detect_blue_regions(screenshot)
    
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


    if enable_color and blue_mask is not None:
        # Find contours of blue regions
        contours, _ = cv2.findContours(blue_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for idx, cnt in enumerate(contours):
            x, y, w, h = cv2.boundingRect(cnt)
            # Skip noise or tiny regions - buttons are usually larger
            if w < 25 or h < 15:
                continue
            
            # Add padding to the crop to help Tesseract
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
                # 2. Binarization (Assume white text on dark background -> Invert to get black on white)
                # We'll use Otsu thresholding with inversion
                _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
                # 3. Upscale 2x
                upscaled = cv2.resize(thresh, (0,0), fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
                
                # Run OCR on the upscaled crop with PSM 6 (Assume single block of text)
                config_str = '--psm 6'
                data = pytesseract.image_to_data(upscaled, config=config_str, output_type=pytesseract.Output.DICT)
                
                # --- Full Region Text Matching ---
                # Sometimes Tesseract splits words. We check the joined text of the entire region.
                full_region_text = " ".join([t.strip() for t in data['text'] if t.strip()])
                if full_region_text:
                    # Use the bounding box of the entire region (not just one word)
                    full_abs_box = (offset_x + x, offset_y + y, w, h)
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
                # Adjusted for 2x upscale: data['left'][i] / 2
                abs_x = offset_x + x_pad + (data['left'][i] // 2)
                abs_y = offset_y + y_pad + (data['top'][i] // 2)
                abs_w = data['width'][i] // 2
                abs_h = data['height'][i] // 2
                abs_box = (abs_x, abs_y, abs_w, abs_h)
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
            
            process_text_match(text, text_lower, conf, abs_box, target_keywords_click, target_keywords_type, matches, app_bounds)


    return matches

def process_text_match(text, text_lower, conf, abs_box, target_keywords_click, target_keywords_type, matches, app_bounds=None):
    """Refactored matching logic used by both scan paths."""
    # Safety: check if this coordinate is within our own app window
    if app_bounds and is_box_in_app_window(abs_box, app_bounds):
        # logger.debug(f"Ignoring keyword '{text}' as it is within the app's own window.")
        return matches

    # Check CLICK keywords
    for k in target_keywords_click:
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

