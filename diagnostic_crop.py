import cv2
import numpy as np
import pytesseract
from PIL import Image
import os
import json

# Ensure Tesseract path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def diagnostic_crop(path):
    print(f"Analyzing {path}...")
    img = cv2.imread(path)
    if img is None:
        print("Failed to load image.")
        return
        
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Try different PSM modes on the crop
    for psm in [6, 7, 8, 10]:
        config = f'--psm {psm}'
        data = pytesseract.image_to_data(gray, config=config, output_type=pytesseract.Output.DICT)
        text = " ".join([t.strip() for t in data['text'] if t.strip()])
        print(f"PSM {psm}: '{text}'")
        
    # Also simulate the thresholding/upscaling from the main OCR logic
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    upscaled = cv2.resize(thresh, (0,0), fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    cv2.imwrite("diagnostic_upscaled.png", upscaled)
    
    print("\nWith preprocessing (upscale 3x):")
    for psm in [6, 7, 8, 10]:
        config = f'--psm {psm}'
        data = pytesseract.image_to_data(upscaled, config=config, output_type=pytesseract.Output.DICT)
        text = " ".join([t.strip() for t in data['text'] if t.strip()])
        print(f"PSM {psm}: '{text}'")

if __name__ == "__main__":
    diagnostic_crop("debug_manager_crop.png")
