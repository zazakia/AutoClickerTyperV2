import cv2
import numpy as np
import pytesseract
from PIL import Image
import os
import json
from core.ocr import capture_screen, get_target_region

# Ensure Tesseract path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def debug_manager_window():
    region = get_target_region()
    print(f"Target Region: {region}")
    
    if region == (0, 0, 0, 0) or region is None:
        print("Manager window not found. Capturing full screen as fallback.")
        region = None
    
    screenshot = capture_screen(region=region)
    screenshot.save("debug_manager_crop.png")
    
    # Run full OCR on the crop
    print("Running OCR on target region...")
    data = pytesseract.image_to_data(screenshot, output_type=pytesseract.Output.DICT)
    
    found_text = []
    for i in range(len(data['text'])):
        text = data['text'][i].strip()
        if text:
            found_text.append((text, data['left'][i], data['top'][i], data['conf'][i]))
            print(f"Found: '{text}' at ({data['left'][i]}, {data['top'][i]}) Conf: {data['conf'][i]}")

    with open("debug_manager_ocr.json", "w") as f:
        json.dump(found_text, f, indent=4)
    print("Results saved to debug_manager_ocr.json")

if __name__ == "__main__":
    debug_manager_window()
