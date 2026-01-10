import cv2
import numpy as np
import pyautogui
import pytesseract
from PIL import Image
import config
from utils.logger import logger
import os

# Set Tesseract Command
if os.path.exists(config.TESSERACT_CMD_PATH):
    pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_CMD_PATH
else:
    logger.warning(f"Tesseract not found at configured path: {config.TESSERACT_CMD_PATH}. Assuming it is in PATH.")

import pygetwindow as gw

def capture_screen(region=None):
    """Captures the screen or a specific region (x, y, w, h)."""
    return pyautogui.screenshot(region=region)

def get_target_region():
    """
    Returns the (x, y, w, h) of the target window if configured and found.
    Returns None if full screen should be used.
    """
    if config.TARGET_WINDOW_TITLE:
        try:
            # Filter windows by title
            windows = gw.getWindowsWithTitle(config.TARGET_WINDOW_TITLE)
            if windows:
                # Pick the first matching window
                win = windows[0]
                # Ensure it has a valid size
                if win.width > 0 and win.height > 0:
                     return (win.left, win.top, win.width, win.height)
            else:
                logger.warning(f"Target window '{config.TARGET_WINDOW_TITLE}' not found. Skipping scan.")
                # We return a 0-size rect to indicate 'do not scan' or special sentinel
                # For safety, if user WANTS restriction, we shouldn't fail-open to full screen.
                return (0, 0, 0, 0) 
        except Exception as e:
            logger.error(f"Error finding window: {e}")
            return (0, 0, 0, 0)
    return None

def detect_blue_regions(screenshot):
    """
    Detects blue-colored regions in the screenshot using HSV color space.
    Returns a binary mask where blue regions are white (255) and others are black (0).
    """
    if not config.ENABLE_COLOR_FILTER:
        return None
    
    try:
        # Convert PIL Image to OpenCV format (BGR)
        img_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        
        # Convert to HSV color space
        hsv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2HSV)
        
        # Create mask for blue color range
        lower_blue = np.array(config.BLUE_HSV_LOWER)
        upper_blue = np.array(config.BLUE_HSV_UPPER)
        mask = cv2.inRange(hsv, lower_blue, upper_blue)
        
        # Apply morphological operations to reduce noise
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        
        return mask
    except Exception as e:
        logger.error(f"Blue region detection failed: {e}")
        return None

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
        return overlap_ratio >= config.COLOR_OVERLAP_THRESHOLD
    except Exception as e:
        logger.error(f"Error checking blue background: {e}")
        return False

def scan_for_keywords(target_keywords_click, target_keywords_type):
    """
    Scans the screen (or target window) for keywords.
    Returns a list of dicts: {'keyword': str, 'type': 'CLICK'|'TYPE', 'box': (x, y, w, h), 'conf': float}
    """
    region = get_target_region()
    
    # Handle case where window wasn't found - don't scan full screen if restricted
    if region == (0, 0, 0, 0):
        return []

    screenshot = capture_screen(region=region)
    
    # Region offset for coordinate mapping (0,0 if full screen)
    offset_x, offset_y = region[0], region[1] if region else (0, 0)
    
    # Detect blue regions if color filtering is enabled
    blue_mask = detect_blue_regions(screenshot)
    if config.ENABLE_COLOR_FILTER and blue_mask is not None:
        logger.debug("Blue region detection enabled")

    # Get detailed data including boxes and confidence
    try:
        data = pytesseract.image_to_data(screenshot, output_type=pytesseract.Output.DICT)
    except Exception as e:
        logger.error(f"OCR Failed: {e}")
        return []

    matches = []
    
    n_boxes = len(data['text'])
    for i in range(n_boxes):
        text = data['text'][i].strip()
        conf = int(data['conf'][i])
        
        if not text:
            continue

        if conf < config.OCR_CONFIDENCE_THRESHOLD:
            continue
        
        text_lower = text.lower()
        
        # Calculate ABSOLUTE screen coordinates
        # Tesseract gives x,y relative to the screenshot image
        # box = (x, y, w, h)
        abs_x = offset_x + data['left'][i]
        abs_y = offset_y + data['top'][i]
        abs_w = data['width'][i]
        abs_h = data['height'][i]
        abs_box = (abs_x, abs_y, abs_w, abs_h)
        
        # Check if text is on a blue background (if filtering is enabled)
        on_blue = is_on_blue_background(abs_box, blue_mask, (offset_x, offset_y))
        
        if not on_blue and config.ENABLE_COLOR_FILTER:
            # Skip this match if it's not on a blue background
            continue
        
        # Check CLICK keywords
        for k in target_keywords_click:
            if text_lower == k.lower():
                matches.append({
                    'keyword': k,
                    'found_text': text,
                    'type': 'CLICK',
                    'box': abs_box,
                    'conf': conf
                })
                logger.debug(f"Found '{k}' on blue background at {abs_box}")
        
        # Check TYPE keywords
        for k in target_keywords_type:
            if text_lower == k.lower():
                matches.append({
                    'keyword': k,
                    'found_text': text,
                    'type': 'TYPE',
                    'box': abs_box,
                    'conf': conf
                })
                logger.debug(f"Found '{k}' on blue background at {abs_box}")

    return matches
