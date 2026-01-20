import cv2
import numpy as np
import pytesseract
from PIL import Image
import os
import json

# Load config to get tesseract path
try:
    with open('config.json', 'r') as f:
        cfg = json.load(f)
    tesseract_cmd = cfg.get("TESSERACT_CMD_PATH", r'C:\Program Files\Tesseract-OCR\tesseract.exe')
    if os.path.exists(tesseract_cmd):
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
except:
    pass

def diagnostic_ocr(image_path):
    if not os.path.exists(image_path):
        print(f"File not found: {image_path}")
        return

    print(f"Analyzing {image_path}...")
    screenshot = Image.open(image_path)
    img_np = np.array(screenshot)
    
    # Simulate detect_blue_regions
    img_cv = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
    hsv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2HSV)
    lower_blue = np.array([100, 50, 50])
    upper_blue = np.array([130, 255, 255])
    mask = cv2.inRange(hsv, lower_blue, upper_blue)
    
    # Save mask for inspection
    cv2.imwrite('debug_mask.png', mask)
    
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    print(f"Found {len(contours)} blue regions.")
    
    for i, cnt in enumerate(contours):
        x, y, w, h = cv2.boundingRect(cnt)
        if w < 10 or h < 5: continue
        
        pad = 5
        x_p, y_p = max(0, x-pad), max(0, y-pad)
        w_p, h_p = min(img_np.shape[1]-x_p, w+pad*2), min(img_np.shape[0]-y_p, h+pad*2)
        
        crop = img_np[y_p:y_p+h_p, x_p:x_p+w_p]
        
        # Preprocessing
        gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        upscaled = cv2.resize(thresh, (0,0), fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        
        data = pytesseract.image_to_data(upscaled, output_type=pytesseract.Output.DICT)
        
        found = []
        for j in range(len(data['text'])):
            t = data['text'][j].strip()
            if t:
                found.append(f"'{t}'({data['conf'][j]})")
        
        print(f"Region {i} at ({x},{y},{w},{h}): {' '.join(found)}")

if __name__ == "__main__":
    diagnostic_ocr('test_artifact_1_harness_start.png')
