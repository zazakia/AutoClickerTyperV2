import time
import sys
import pyautogui
import threading
from core.config_manager import config_manager
from core.ocr import scan_for_keywords, get_target_region
from core.actions import perform_click, perform_type, perform_shortcut, scroll_all_scrollbars
from core.verification import verify_action
from utils.logger import logger, log_action
from core.exceptions import ActionError, OCRError, ConfigError

# Global stop event for GUI control
stop_event = threading.Event()

# Global Stats for GUI feedback
stats = {
    "scans": 0,
    "matches": 0,
    "clicks": 0,
    "avg_speed": 0.0,
    "total_scan_time": 0.0
}

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
        
    # Test 2: OCR System (Check if Tesseract is accessible)
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        logger.info("TEST PASS: OCR System (Tesseract) accessible.")
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
    last_shortcut_time = float(0)
    SHORTCUT_INTERVAL = 10 
    last_scroll_time = float(0)
    cycle_count = 0
    
    try:
        while not stop_event.is_set():
            try:
                current_time = time.time()
                # 0. Run Shortcuts (Periodic or initial)
                current_time = time.time()
                if current_time - last_shortcut_time > SHORTCUT_INTERVAL:
                    shortcuts = config_manager.get("SHORTCUT_SEQUENCE")
                    if shortcuts:
                        logger.info("Running Workflow Shortcuts...")
                        for step in shortcuts:
                            if stop_event.is_set(): break
                            perform_shortcut(step['keys'])
                            time.sleep(step['delay'])
                        last_shortcut_time = time.time()
                        time.sleep(1.0) # Wait for UI to settle

                # 1. Scroll All Scrollbars (Periodic)
                if config_manager.get("AUTO_SCROLL_ENABLED", True):
                    SCROLL_INTERVAL = config_manager.get("SCROLL_INTERVAL", 5.0)
                    if current_time - last_scroll_time > SCROLL_INTERVAL:
                        logger.debug("Checking for scrollbars...")
                        if scroll_all_scrollbars():
                            last_scroll_time = time.time()
                            time.sleep(0.5) # Wait for UI to settle after scrolling
                        else:
                            last_scroll_time = time.time()

                # 2. Scan
                scan_start_time = time.time()
                logger.debug("Scanning screen...")
                
                # Multi-window support (could be added here, currently sticking to existing behavior but adding dedup)
                matches = scan_for_keywords(config_manager.get("CLICK_KEYWORDS", []), config_manager.get("TYPE_KEYWORDS", []))
                
                # Update Stats
                stats["scans"] += 1
                stats["matches"] += len(matches)
                
                if not matches:
                    logger.debug("No target keywords detected. Waiting...")
                    time.sleep(config_manager.get("SCAN_INTERVAL", 0.5))
                    continue

                logger.info(f"Detected {len(matches)} potential targets.")
                
                # 2. Decision Engine
                matches.sort(key=lambda x: x['conf'], reverse=True)
                
                targets_to_process = matches if config_manager.get("CLICK_ALL_MATCHES", True) else [matches[0]]
                
                # Clear stale retries from map occasionally (every 20 cycles)
                cycle_count += 1
                if cycle_count % 20 == 0:
                    keys_to_delete = [k for k, v in retry_map.items() if isinstance(v, dict) and current_time - v.get('time', 0) > 60]
                    for k in keys_to_delete:
                        retry_map.pop(k, None)
                
                # Deduplication map for THIS cycle
                already_clicked_this_cycle = set()
                
                for target in targets_to_process:
                    if stop_event.is_set(): break
                    
                    keyword = target['keyword']
                    action_type = target['type']
                    box = target['box']
                    
                    # Proximity matches target permanent UI text that never disappears,
                    # so they should not go through the disappear-based retry/verify system.
                    is_proximity = keyword.startswith("Proximity(")

                    # Anchor keywords (Bell, El, etc.) serve as proximity anchors only.
                    # They should never be clicked directly - instead, look for proximity matches.
                    anchor_keywords = config_manager.get("ANCHOR_KEYWORDS", [])
                    is_anchor_only = keyword in anchor_keywords and not is_proximity

                    if is_anchor_only:
                        logger.debug(f"Skipping anchor '{keyword}'...")
                        continue

                    # Check Retry Limits (skip for proximity matches)
                    # Use a coarser 20px grid to group slight OCR box jitter
                    rx, ry = int(box[0] // 20) * 20, int(box[1] // 20) * 20
                    retry_key = f"{keyword}_{rx}_{ry}"
                    
                    retry_data = retry_map.get(retry_key, {'count': 0, 'time': current_time})
                    current_retries = retry_data['count']
                    
                    if not is_proximity and current_retries >= config_manager.get("MAX_RETRY_ATTEMPTS", 3):
                        logger.warning(f"Max retries reached for '{keyword}' at ({rx},{ry}). Skipping temporarily.")
                        continue
                        
                    # Deduplication check
                    if config_manager.get("CLICK_DEDUP_ENABLED", True):
                        if retry_key in already_clicked_this_cycle:
                            logger.debug(f"Skipping duplicate target in this cycle: {keyword} at ({rx},{ry})")
                            continue
                        already_clicked_this_cycle.add(retry_key)

                    logger.info(f"Engaging Target: {keyword} ({action_type})")
                    
                    # 3. Action
                    success = False
                    if action_type == 'CLICK':
                        click_types = config_manager.get("KEYWORD_CLICK_TYPES", {})
                        click_type = click_types.get(keyword, "single")
                        coords = perform_click(box, click_type=click_type)
                        success = True 
                    elif action_type == 'TYPE':
                        success = perform_type(keyword, box)
                    
                    if not success:
                        logger.error("Action execution failed (False returned).")
                        continue

                    # 4. Verification (skip for proximity matches - target text is permanent UI)
                    if is_proximity:
                        verified = True
                        reason = "Proximity match - verification skipped"
                        retry_map[retry_key] = {'count': 0, 'time': current_time}
                    else:
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
                        logger.info(f"Action Verified: Success{' (proximity - skipped verify)' if is_proximity else ''}")
                        stats["clicks"] += 1
                        retry_map[retry_key] = {'count': 0, 'time': current_time}
                    else:
                        logger.warning(f"Verification Failed: Object still present")
                        retry_map[retry_key] = {'count': current_retries + 1, 'time': current_time}
                    
                    time.sleep(config_manager.get("ACTION_DELAY", 0.1))
                
                # Scan summary
                duration = time.time() - scan_start_time
                stats["total_scan_time"] += duration
                if stats["scans"] > 0: # Avoid division by zero if somehow scans is 0
                    stats["avg_speed"] = stats["total_scan_time"] / stats["scans"]
                logger.info(f"Scan cycle completed in {duration:.2f}s")
                time.sleep(config_manager.get("SCAN_INTERVAL", 0.5))

            except ActionError as e:
                logger.error(f"Action failed: {e}")
                time.sleep(1)
            except OCRError as e:
                logger.error(f"OCR failed: {e}")
                time.sleep(1)
            except ConfigError as e:
                logger.critical(f"Configuration error: {e}. Stopping bot.")
                break
            except Exception as e:
                 logger.error(f"Unexpected error in loop: {e}")
                 # Log full traceback only in debug mode to avoid clutter
                 if config_manager.get("DEBUG_MODE"):
                     logger.debug("Traceback:", exc_info=True)
                 time.sleep(1)

    except KeyboardInterrupt:
        logger.info("User stopped execution.")
    except Exception as e:
        logger.critical(f"Critical Failure: {e}", exc_info=True)

if __name__ == "__main__":
    main()
