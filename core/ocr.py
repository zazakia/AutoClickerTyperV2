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

    return matches
