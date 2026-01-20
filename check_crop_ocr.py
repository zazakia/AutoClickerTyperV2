import cv2
import numpy as np
import pytesseract
from PIL import Image
import os

# Ensure Tesseract path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def check_crop(path):
    print(f"Checking {path}...")
    crop = cv2.imread(path)
    if crop is None:
        print("Failed to load image.")
        return
        
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    upscaled = cv2.resize(thresh, (0,0), fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    
    cv2.imwrite("last_thresh.png", upscaled)
    
    print("Running OCR (default)...")
    data = pytesseract.image_to_data(upscaled, output_type=pytesseract.Output.DICT)
    print(f"Result (Default): {[t for t in data['text'] if t.strip()]}")
    
    print("Running OCR (PSM 6)...")
    data6 = pytesseract.image_to_data(upscaled, config='--psm 6', output_type=pytesseract.Output.DICT)
    print(f"Result (PSM 6): {[t for t in data6['text'] if t.strip()]}")
    
    print("Running OCR (PSM 7)...")
    data7 = pytesseract.image_to_data(upscaled, config='--psm 7', output_type=pytesseract.Output.DICT)
    print(f"Result (PSM 7): {[t for t in data7['text'] if t.strip()]}")

if __name__ == "__main__":
    check_crop("debug_crop_raw.png")
