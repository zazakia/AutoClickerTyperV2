import logging
import sys
from datetime import datetime
import config

def setup_logger():
    """Configures and returns a structured logger."""
    logger = logging.getLogger("AutoClicker")
    logger.setLevel(config.LOG_VERBOSITY)

    # Console Handler
    c_handler = logging.StreamHandler(sys.stdout)
    c_handler.setLevel(config.LOG_VERBOSITY)

    # File Handler
    f_handler = logging.FileHandler('execution.log')
    f_handler.setLevel(config.LOG_VERBOSITY)

    # Formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    c_handler.setFormatter(formatter)
    f_handler.setFormatter(formatter)

    logger.addHandler(c_handler)
    logger.addHandler(f_handler)

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
