import json
from core.ocr import scan_for_keywords
from core.config_manager import config_manager
from utils.logger import logger

def dump_all_segments():
    config_manager.set("TARGET_WINDOW_TITLE", "Manager")
    # We call scan_for_keywords with nonsense keywords to get all_segments indirectly 
    # Or just modify scan_for_keywords to return them?
    # Actually, I'll just use the capture/OCR logic directly here.
    from core.ocr import capture_screen, get_target_region
    import pytesseract
    import numpy as np
    
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    
    region = get_target_region()
    screenshot = capture_screen(region=region)
    data = pytesseract.image_to_data(screenshot, output_type=pytesseract.Output.DICT)
    
    all_segments = []
    for i in range(len(data['text'])):
        text = data['text'][i].strip()
        if text:
            all_segments.append({
                "text": text,
                "x": data['left'][i],
                "y": data['top'][i],
                "w": data['width'][i],
                "h": data['height'][i],
                "conf": data['conf'][i]
            })
            
    with open("all_segments_manager.json", "w") as f:
        json.dump(all_segments, f, indent=4)
    print("Dumping complete.")

if __name__ == "__main__":
    dump_all_segments()
