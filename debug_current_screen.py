import cv2
import numpy as np
import pytesseract
from PIL import Image
import os
import json
from core.ocr import capture_screen

# Ensure Tesseract path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def debug_current_screen():
    print("Capturing screen...")
    screenshot = capture_screen()
    screenshot.save("debug_current_full.png")
    img_np = np.array(screenshot)
    
    # Run full OCR
    print("Running full OCR...")
    data = pytesseract.image_to_data(screenshot, output_type=pytesseract.Output.DICT)
    
    found_text = []
    for i in range(len(data['text'])):
        text = data['text'][i].strip()
        if text:
            found_text.append((text, data['left'][i], data['top'][i], data['conf'][i]))
            if "Bell" in text or "El" in text or "ll" in text:
                print(f"Potential Anchor Found: '{text}' at ({data['left'][i]}, {data['top'][i]}) Conf: {data['conf'][i]}")

    with open("debug_ocr_results.json", "w") as f:
        json.dump(found_text, f, indent=4)
    print("Results saved to debug_ocr_results.json")

if __name__ == "__main__":
    debug_current_screen()
