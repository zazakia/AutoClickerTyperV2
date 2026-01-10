import logging

# Keywords to CLICK
CLICK_KEYWORDS = [
    "Accept",
    "Run",
    "Allow",
    "Allow Always",
    "Proceed",
    "Yes",
    "OK",
    "Confirm"
]

# Keywords to TYPE
TYPE_KEYWORDS = [
    "proceed"
]

# Runtime Settings
OCR_CONFIDENCE_THRESHOLD = 60  # Minimum confidence (0-100)
SCAN_INTERVAL = 0.5            # Seconds between full scans
MAX_RETRY_ATTEMPTS = 3         # Retries per keyword action
ACTION_DELAY = 0.1             # Delay between moving and clicking/typing
LOG_VERBOSITY = logging.INFO
ALWAYS_ON_TOP = False

# ... settings ...

# Window Targeting
# If set, the bot will ONLY scan and interact within the window containing this title.
# Set to None or "" to scan the entire screen.
import os
TARGET_WINDOW_TITLE = os.getenv("TARGET_WINDOW_TITLE", "Manager")
TESSERACT_CMD_PATH = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Special Workflow Actions
# Define sequences of keys to press before scanning or as part of the loop
SHORTCUT_SEQUENCE = [
    {'keys': ['ctrl', 'b'], 'delay': 0.5},
    {'keys': ['ctrl', 'i'], 'delay': 0.5}
]
