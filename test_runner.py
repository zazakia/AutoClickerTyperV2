import subprocess
import time
import os
import sys
import pyautogui
from utils.logger import setup_logger

logger = setup_logger()

def run_test_scenario():
    logger.info("Starting Test Scenario...")

    # 1. Start Test Harness (GUI)
    # We use subprocess.Popen to run it in background
    start_log_pos = 0
    if os.path.exists("execution.log"):
        with open("execution.log", "r") as f:
            f.seek(0, 2) # Seek to end
            start_log_pos = f.tell()
        
    logger.info("Launching Test Harness...")
    harness_process = subprocess.Popen([sys.executable, "test_harness.py"], cwd=os.getcwd())
    
    # Give it time to render
    time.sleep(3)
    
    # Capture Screenshot 1: Harness Initial State
    pyautogui.screenshot("test_artifact_1_harness_start.png")
    logger.info("Captured initial state screenshot.")

    # 2. Start Main Bot
    logger.info("Launching Auto Clicker Bot...")
    env = os.environ.copy()
    env["TARGET_WINDOW_TITLE"] = "Auto Clicker Test Harness"
    bot_process = subprocess.Popen([sys.executable, "main.py"], cwd=os.getcwd(), env=env)

    # 3. Monitor for a duration
    # We expect the bot to find keywords like "Accept", "Run", "Allow" in the harness
    # and click them, causing them to disappear.
    
    duration = 30
    logger.info(f"Monitoring for {duration} seconds...")
    
    for i in range(duration):
        time.sleep(1)
        if i % 5 == 0:
            logger.info(f"Test running... {i}s")
    
    # Capture Screenshot 2: Harness End State (Should be empty or mostly empty)
    pyautogui.screenshot("test_artifact_2_harness_end.png")
    logger.info("Captured end state screenshot.")

    # 4. Cleanup
    logger.info("Terminating processes...")
    bot_process.terminate()
    harness_process.terminate()
    
    # 5. Analysis
    # We can check execution.log for "Action Verified"
    if os.path.exists("execution.log"):
        with open("execution.log", "r") as f:
            f.seek(start_log_pos)
            logs = f.read()
            success_count = logs.count("Action Verified: Keyword disappeared")
            logger.info(f"Found {success_count} verified actions in the NEW log entries.")
            
            if success_count > 0:
                logger.info("TEST RESULT: PASS")
            else:
                logger.info("TEST RESULT: FAIL (No verified actions)")
    else:
        logger.error("No execution log found.")

if __name__ == "__main__":
    run_test_scenario()
