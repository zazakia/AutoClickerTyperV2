import pyautogui
import time
import random
from core.config_manager import config_manager
from utils.logger import logger
from core.exceptions import ActionError
from core.ocr import detect_scrollbars

def get_target_window():
    import re
    import pygetwindow as gw
    title_pattern = config_manager.get("TARGET_WINDOW_REGEX", "")
    title = config_manager.get("TARGET_WINDOW_TITLE", "")
    try:
        if title_pattern:
            for w in gw.getAllWindows():
                if re.search(title_pattern, w.title, re.IGNORECASE):
                    return w
        elif title:
            wins = gw.getWindowsWithTitle(title)
            if wins:
                return wins[0]
    except Exception as e:
        logger.error(f"Failed to get target window: {e}")
    return None

def smooth_move(x, y):
    """Moves mouse smoothly to x, y."""
    try:
        # Improved human-like movement with intermediate waypoints could be added here
        pyautogui.moveTo(x, y, duration=random.uniform(0.05, 0.15))
    except Exception as e:
        logger.error(f"Failed to move mouse: {e}")
        raise ActionError(f"Failed to move mouse to ({x}, {y}): {e}")

def apply_random_offset(x, y, w, h):
    """Calculates a random point within the center ±5% bounding box for precise targeting."""
    center_x = x + w / 2
    center_y = y + h / 2
    
    # Very small random offset around the center (±5% of dimensions)
    max_offset_x = max(1, w * 0.05)
    max_offset_y = max(1, h * 0.05)
    
    offset_x = random.uniform(-max_offset_x, max_offset_x)
    offset_y = random.uniform(-max_offset_y, max_offset_y)
    
    return int(center_x + offset_x), int(center_y + offset_y)

def perform_click(box, click_type="single"):
    """Performs a precise human-like click on the target box."""
    try:
        import numpy as np
        # Window focus guard
        win = get_target_window()
        if win and not win.isActive:
            logger.info(f"Restoring focus to window: {win.title}")
            try:
                win.activate()
                time.sleep(0.1) 
            except Exception as e:
                logger.debug(f"Could not activate window: {e}")

        x, y, w, h = box
        target_x, target_y = apply_random_offset(x, y, w, h)
        
        # Pixel verification setup
        pixel_before = None
        if config_manager.get("CLICK_VERIFY_PIXEL", True):
            try:
                pixel_before = pyautogui.pixel(target_x, target_y)
            except: pass

        logger.debug(f"Moving to click ({click_type}) at ({target_x}, {target_y})")
        smooth_move(target_x, target_y)
        
        time.sleep(random.uniform(0.02, 0.08)) 
        
        if click_type == "double":
            pyautogui.doubleClick()
        elif click_type == "right":
            pyautogui.rightClick()
        else:
            pyautogui.click()
        
        # Move mouse slightly away
        pyautogui.moveRel(0, 25, duration=0.1)
        
        # Quick verify
        if pixel_before and config_manager.get("CLICK_VERIFY_PIXEL", True):
            time.sleep(0.1)
            try:
                pixel_after = pyautogui.pixel(target_x, target_y)
                if pixel_before != pixel_after:
                    logger.debug("Pixel color change detected. Likely success.")
            except: pass

        time.sleep(config_manager.get("ACTION_DELAY", 0.1))
        return (target_x, target_y)
    except ActionError:
        raise 
    except Exception as e:
        logger.error(f"Click action failed: {e}")
        raise ActionError(f"Click failed: {e}")

def perform_type(keyword, box):
    """Clicks the input (box) and types the keyword."""
    # First click to focus
    try:
        perform_click(box)
        
        logger.debug(f"Typing '{keyword}'")
        # Type with random delays between keys
        pyautogui.write(keyword, interval=random.uniform(0.05, 0.15))
        
        time.sleep(0.2)
        pyautogui.press('enter')
        time.sleep(config_manager.get("ACTION_DELAY", 0.1))
        return True
    except ActionError:
         # perform_click already logged the error, but we might want to wrap context
         raise 
    except Exception as e:
        logger.error(f"Typing failed: {e}")
        raise ActionError(f"Typing failed: {e}")

def perform_shortcut(keys):
    """Executes a keyboard shortcut combination."""
    try:
        logger.info(f"Pressing shortcut: {'+'.join(keys)}")
        pyautogui.hotkey(*keys)
        return True
    except Exception as e:
        logger.error(f"Shortcut failed: {e}")
        raise ActionError(f"Shortcut failed: {e}")

def perform_scroll(box, amount=-500):
    """Moves to a location and scrolls."""
    try:
        x, y, w, h = box
        # Target slightly to the left of the scrollbar thumb to ensure we are in the scrollable area
        target_x = max(0, x - 20)
        target_y = y + h // 2
        
        logger.debug(f"Moving to scroll at ({target_x}, {target_y})")
        smooth_move(target_x, target_y)
        time.sleep(0.1)
        
        pyautogui.scroll(amount)
        logger.info(f"Scrolled {amount} units at {target_x}, {target_y}")
        time.sleep(config_manager.get("ACTION_DELAY", 0.1))
        return True
    except Exception as e:
        logger.error(f"Scroll action failed: {e}")
        return False

def scroll_all_scrollbars(region=None):
    """
    Finds all scrollbars and scrolls down.
    """
    scrollbars = detect_scrollbars(region=region)
    if not scrollbars:
        return False
        
    logger.info(f"Found {len(scrollbars)} scrollbar(s) to interact with.")
    success = False
    for box in scrollbars:
        if perform_scroll(box, amount=config_manager.get("SCROLL_AMOUNT", -1000)):
            success = True
            
    return success
