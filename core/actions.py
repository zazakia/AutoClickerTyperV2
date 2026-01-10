import pyautogui
import time
import random
import config
from utils.logger import logger

def smooth_move(x, y):
    """Moves mouse smoothly to x, y."""
    # PyAutoGUI has built-in tweening, but we can just use a simple duration
    pyautogui.moveTo(x, y, duration=random.uniform(0.1, 0.3))

def apply_random_offset(x, y, w, h):
    """Calculates a random point within the bounding box."""
    # Stay within central 80% to be safe
    offset_x = random.randint(int(w * 0.1), int(w * 0.9))
    offset_y = random.randint(int(h * 0.1), int(h * 0.9))
    return x + offset_x, y + offset_y

def perform_click(box):
    """Performs a human-like click on the target box."""
    x, y, w, h = box
    target_x, target_y = apply_random_offset(x, y, w, h)
    
    logger.debug(f"Moving to click at ({target_x}, {target_y})")
    smooth_move(target_x, target_y)
    
    time.sleep(random.uniform(0.05, 0.15)) # Pre-click delay
    pyautogui.click()
    time.sleep(config.ACTION_DELAY)
    
    return (target_x, target_y)

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
        time.sleep(config.ACTION_DELAY)
        return True
    except Exception as e:
        logger.error(f"Typing failed: {e}")
        return False

def perform_shortcut(keys):
    """Executes a keyboard shortcut combination."""
    try:
        logger.info(f"Pressing shortcut: {'+'.join(keys)}")
        pyautogui.hotkey(*keys)
        return True
    except Exception as e:
        logger.error(f"Shortcut failed: {e}")
        return False
