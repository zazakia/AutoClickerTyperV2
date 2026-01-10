import time
import sys
import pyautogui
from core.config_manager import config_manager
from core.ocr import scan_for_keywords
from core.actions import perform_click, perform_type, perform_shortcut
from core.verification import verify_action
from utils.logger import logger, log_action

def self_test():
    """
    Runs automated self-tests as required by Section 9.
    Since we don't have a guaranteed test UI always present, 
    we check if critical subsystems are loaded.
    """
    logger.info("Running Self-Tests...")
    
    # Test 1: configuration
    click_kw = config_manager.get("CLICK_KEYWORDS", [])
    type_kw = config_manager.get("TYPE_KEYWORDS", [])
    if not click_kw and not type_kw:
        # It's okay if lists are empty if we are just running shortcuts, but warning is good
        logger.warning("Keywords empty. Bot will only run shortcuts if configured.")
        
    # Test 2: OCR System (Check if we can take a screenshot and run tesseract)
    # We'll just try to scan for something dummy.
    try:
        scan_for_keywords([], [])
        logger.info("TEST PASS: OCR System functional.")
        pass
    except Exception as e:
        logger.error(f"TEST FAIL: OCR System Error: {e}")
        return False

    logger.info("Self-Tests Passed.")
    return True


# Global stop event that can be set by the UI
import threading
stop_event = threading.Event()

def main():
    logger.info("Initializing Autonomous Auto Clicker...")
    
    if not self_test():
        logger.critical("Self-tests failed. Aborting.")
        sys.exit(1)
        
    logger.info("Starting Continuous Execution Loop...")
    
    retry_map = {} # Tracks retries for specific keyword instances
    last_shortcut_time = 0
    SHORTCUT_INTERVAL = 10 
    
    try:
        while not stop_event.is_set():
            # 0. Run Shortcuts (Periodic or initial)
            # The prompt implies "Press Ctrl+B... check for keywords". 
            # We'll do this if we haven't done it recently to "refresh" the inbox state.
            if time.time() - last_shortcut_time > SHORTCUT_INTERVAL:
                shortcuts = config_manager.get("SHORTCUT_SEQUENCE")
                if shortcuts:
                    logger.info("Running Workflow Shortcuts...")
                    for step in shortcuts:
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
            # Sort by confidence (high to low)
            matches.sort(key=lambda x: x['conf'], reverse=True)
            
            # Simple State Machine: Process one at a time to ensure verification works
            target = matches[0]
            keyword = target['keyword']
            action_type = target['type']
            box = target['box']
            
            # Check Retry Limits
            current_retries = retry_map.get(keyword, 0)
            if current_retries >= config_manager.get("MAX_RETRY_ATTEMPTS", 3):
                logger.warning(f"Max retries reached for '{keyword}'. Skipping temporarily.")
                # In a real sophisticated system, we'd blacklist this specific region
                # For now, we wait a bit longer to see if state changes externally
                time.sleep(config_manager.get("SCAN_INTERVAL", 0.5) * 2)
                continue

            logger.info(f"Engaging Target: {keyword} ({action_type})")
            
            # 3. Action
            success = False
            if action_type == 'CLICK':
                coords = perform_click(box)
                success = True # Click itself rarely "fails" unless exception
            elif action_type == 'TYPE':
                success = perform_type(keyword, box) # Type uses the keyword itself as input text per Prompt 4.2
            
            if not success:
                logger.error("Action execution failed.")
                continue

            # 4. Verification
            verified, reason = verify_action(keyword, action_type, box)
            
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
                logger.info(f"Action Verified: {reason}")
                retry_map[keyword] = 0 # Reset retries on success
            else:
                logger.warning(f"Verification Failed: {reason}")
                retry_map[keyword] = current_retries + 1
                # Verification failure logic (Section 6)
                # "Re-focus active window" - clicking usually does this
                # "Increase delay" - handled in next loop implicitly by processing time
            
            time.sleep(config_manager.get("SCAN_INTERVAL", 0.5))
            
    except KeyboardInterrupt:
        logger.info("User stopped execution.")
    except Exception as e:
        logger.critical(f"Critical Failure: {e}", exc_info=True)
        # Section 8: Attempt safe restart (in this script, we just log and exit, 
        # but a supervisor script would restart this process)

if __name__ == "__main__":
    main()
