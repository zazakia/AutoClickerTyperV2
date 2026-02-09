import logging
import sys
from datetime import datetime
from core.config_manager import config_manager
import os
import config

def setup_logger():
    """Configures and returns a structured logger."""
    logger = logging.getLogger("AutoClicker")
    logger.setLevel(config.LOG_VERBOSITY)

    # Formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # Console Handler
    c_handler = logging.StreamHandler(sys.stdout)
    c_handler.setLevel(config.LOG_VERBOSITY)
    c_handler.setFormatter(formatter)
    logger.addHandler(c_handler)

    # File Handler
    try:
        log_file = os.path.join(config_manager.base_path, "autoclicker.log")
        f_handler = logging.FileHandler(log_file)
        f_handler.setLevel(config.LOG_VERBOSITY)
        f_handler.setFormatter(formatter)
        logger.addHandler(f_handler)
    except Exception as e:
        # Fallback to console only if file logging fails (e.g. permission error)
        # Set console handler to WARNING level to ensure critical errors are still shown
        c_handler.setLevel(logging.WARNING)
        logger.warning(f"Failed to setup log file handler: {e}. Logging to console only.")

    return logger

logger = setup_logger()

def log_action(action_type, keyword, coordinates, verification_result, retry_count, completion_pct):
    """Logs actions in a structured format as requested."""
    logger.info(
        f"ACTION: {action_type} | "
        f"KEYWORD: '{keyword}' | "
        f"COORDS: {coordinates} | "
        f"VERIFIED: {verification_result} | "
        f"RETRY: {retry_count} | "
        f"COMPLETION: {completion_pct}%"
    )
