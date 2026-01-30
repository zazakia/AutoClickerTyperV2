import logging

APP_TITLE = "Zapweb.app Prompt Assist and AutoClicker"


# Keywords to CLICK
CLICK_KEYWORDS = [
    "Accept",
    "Run",
    "Allow",
    "Allow Always",
    "Proceed",
    "Yes",
    "OK",
    "Confirm",
    "Continue",
    "Expand"
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
ALWAYS_ON_TOP = True

# ... settings ...

# Window Targeting
# If set, the bot will ONLY scan and interact within the window containing this title.
# Set to None or "" to scan the entire screen.
import os
TARGET_WINDOW_TITLE = os.getenv("TARGET_WINDOW_TITLE", "")
TESSERACT_CMD_PATH = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Special Workflow Actions
# Define sequences of keys to press before scanning or as part of the loop
SHORTCUT_SEQUENCE = [
    {'keys': ['ctrl', 'b'], 'delay': 0.5},
    {'keys': ['ctrl', 'i'], 'delay': 0.5}
]

# Color Detection Settings
# Enable filtering to only click on buttons with blue backgrounds
ENABLE_COLOR_FILTER = True

# HSV color range for detecting blue buttons
# HSV ranges: Hue (0-180), Saturation (0-255), Value (0-255)
BLUE_HSV_LOWER = [100, 50, 50]   # Lower bound for blue color
BLUE_HSV_UPPER = [130, 255, 255]  # Upper bound for blue color

# Minimum overlap percentage between text box and blue region (0.0 to 1.0)
COLOR_OVERLAP_THRESHOLD = 0.5
