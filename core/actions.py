import pyautogui
import time
import random
from core.config_manager import config_manager
from utils.logger import logger
from core.exceptions import ActionError

def smooth_move(x, y):
    """Moves mouse smoothly to x, y."""
    try:
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

def perform_click(box):
    """Performs a precise human-like click on the target box."""
    try:
        x, y, w, h = box
        target_x, target_y = apply_random_offset(x, y, w, h)
        
        logger.debug(f"Moving to click at ({target_x}, {target_y})")
        smooth_move(target_x, target_y)
        
        time.sleep(random.uniform(0.02, 0.08)) # Pre-click delay
        pyautogui.click()
        
        # Move mouse slightly away down to avoid obscuring the target for verification, but not too far
        pyautogui.moveRel(0, 25, duration=0.1)
        
        time.sleep(config_manager.get("ACTION_DELAY", 0.1))
        
        return (target_x, target_y)
    except ActionError:
        raise # Re-raise known errors
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
