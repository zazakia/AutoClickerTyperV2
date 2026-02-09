import time
import sys
import pyautogui
import threading
from core.config_manager import config_manager
from core.ocr import scan_for_keywords
from core.actions import perform_click, perform_type, perform_shortcut
from core.verification import verify_action
from utils.logger import logger, log_action
from core.exceptions import ActionError, OCRError, ConfigError

# Global stop event for GUI control
stop_event = threading.Event()

def self_test():
    """
    Runs automated self-tests as required by Section 9.
    Checks if critical subsystems are functional.
    """
    logger.info("Running Self-Tests...")
    
    # Test 1: configuration
    click_kw = config_manager.get("CLICK_KEYWORDS", [])
    type_kw = config_manager.get("TYPE_KEYWORDS", [])
    if not click_kw and not type_kw:
        logger.warning("Keywords empty. Bot will only run shortcuts if configured.")
        
    # Test 2: OCR System (Check if we can take a screenshot and run tesseract)
    try:
        scan_for_keywords([], [])
        logger.info("TEST PASS: OCR System functional.")
    except Exception as e:
        logger.error(f"TEST FAIL: OCR System Error: {e}")
        return False

    logger.info("Self-Tests Passed.")
    return True

def main():
    logger.info("Initializing Autonomous Auto Clicker...")
    
    if not self_test():
        logger.critical("Self-tests failed. Aborting.")
        # In a thread, sys.exit(1) might not be ideal, but it's consistent with original logic
        return
        
    logger.info("Starting Continuous Execution Loop...")
    
    retry_map = {} # Tracks retries for specific keyword instances
    last_shortcut_time = 0
    SHORTCUT_INTERVAL = 10 
    
    try:
        while not stop_event.is_set():
            try:
                # 0. Run Shortcuts (Periodic or initial)
                if time.time() - last_shortcut_time > SHORTCUT_INTERVAL:
                    shortcuts = config_manager.get("SHORTCUT_SEQUENCE")
                    if shortcuts:
                        logger.info("Running Workflow Shortcuts...")
                        for step in shortcuts:
                            if stop_event.is_set(): break
                            perform_shortcut(step['keys'])
                            time.sleep(step['delay'])
                        last_shortcut_time = time.time()
                        time.sleep(1.0) # Wait for UI to settle

                # 1. Scan
                logger.debug("Scanning screen...")
                matches = scan_for_keywords(config_manager.get("CLICK_KEYWORDS", []), config_manager.get("TYPE_KEYWORDS", []))
                
                if not matches:
                    logger.debug("No target keywords detected. Waiting...")
                    time.sleep(config_manager.get("SCAN_INTERVAL", 0.5))
                    continue

                logger.info(f"Detected {len(matches)} potential targets.")
                
                # 2. Decision Engine
                matches.sort(key=lambda x: x['conf'], reverse=True)
                
                target = matches[0]
                keyword = target['keyword']
                action_type = target['type']
                box = target['box']
                
                # Check Retry Limits
                rx, ry = int(box[0] // 5) * 5, int(box[1] // 5) * 5
                retry_key = f"{keyword}_{rx}_{ry}"
                
                current_retries = retry_map.get(retry_key, 0)
                if current_retries >= config_manager.get("MAX_RETRY_ATTEMPTS", 3):
                    logger.warning(f"Max retries reached for '{keyword}' at ({rx},{ry}). Skipping temporarily.")
                    time.sleep(config_manager.get("SCAN_INTERVAL", 0.5) * 2)
                    continue

                logger.info(f"Engaging Target: {keyword} ({action_type})")
                
                # 3. Action
                success = False
                if action_type == 'CLICK':
                    coords = perform_click(box)
                    success = True 
                elif action_type == 'TYPE':
                    success = perform_type(keyword, box)
                
                if not success:
                    logger.error("Action execution failed (False returned).")
                    continue

                # 4. Verification
                verified, reason = verify_action(keyword, box)
                
                # 5. Logging & Feedback
                log_action(
                    action_type=action_type,
                    keyword=keyword,
                    coordinates=box,
                    verification_result="PASS" if verified else "FAIL",
                    retry_count=current_retries,
                    completion_pct="N/A"
                )
                
                if verified:
                    logger.info(f"Action Verified: Success")
                    retry_map[retry_key] = 0 # Reset retries on success
                else:
                    logger.warning(f"Verification Failed: Object still present")
                    retry_map[retry_key] = current_retries + 1
                
                time.sleep(config_manager.get("SCAN_INTERVAL", 0.5))

            except ActionError as e:
                logger.error(f"Action failed gracefully: {e}. Retrying loop...")
                time.sleep(1)
            except OCRError as e:
                logger.error(f"OCR failed gracefully: {e}. Retrying loop...")
                time.sleep(1)
            except ConfigError as e:
                logger.critical(f"Configuration error: {e}. Stopping bot.")
                break
            except Exception as e:
                 logger.error(f"Unexpected error in loop: {e}", exc_info=True)
                 time.sleep(1)

    except KeyboardInterrupt:
        logger.info("User stopped execution.")
    except Exception as e:
        logger.critical(f"Critical Failure: {e}", exc_info=True)

if __name__ == "__main__":
    main()
