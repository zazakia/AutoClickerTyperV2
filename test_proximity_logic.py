from core.ocr import _add_proximity_matches
from core.config_manager import config_manager
import logging

# Setup logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test")

# Simulated OCR data from logs
# Android at [119, 635, 53, 11]
# Co. at [178, 635, 16, 11]
all_segments = [
    ("Debugging", (41, 635, 73, 14), 90),
    ("Android", (119, 635, 53, 11), 95),
    ("Co.", (178, 635, 16, 11), 87)
]

config_manager.set("PROXIMITY_CLICKING_ENABLED", True)
config_manager.set("PROXIMITY_DIRECTION", "LEFT")
config_manager.set("PROXIMITY_MAX_DISTANCE", 150)
config_manager.set("ANCHOR_KEYWORDS", ["Co.", "©", "bell"])

matches = []
_add_proximity_matches(matches, all_segments)

print(f"Matches found: {len(matches)}")
for m in matches:
    print(f"  {m['keyword']} -> {m['found_text']} at {m['box']}")
