import pygetwindow as gw
import pyautogui
import pytesseract
from PIL import Image, ImageDraw
import config
import os
import time

# Ensure Tesseract path is set
if os.path.exists(config.TESSERACT_CMD_PATH):
    pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_CMD_PATH

def debug_ocr():
    print("Searching for window with title containing: 'Manager'")
    windows = gw.getWindowsWithTitle("Manager")
    
    if not windows:
        print("ERROR: Window 'Manager' not found.")
        return

    win = windows[0]
    print(f"Found window: '{win.title}' at ({win.left}, {win.top}) - size {win.width}x{win.height}")
    
    if win.width <= 0 or win.height <= 0:
        print("ERROR: Window has invalid dimensions.")
        return
        
    # Capture region
    region = (win.left, win.top, win.width, win.height)
    print(f"Capturing region: {region}")
    screenshot = pyautogui.screenshot(region=region)
    
    # Run OCR
    print("Running OCR...")
    data = pytesseract.image_to_data(screenshot, output_type=pytesseract.Output.DICT)
    
    # Draw results
    draw = ImageDraw.Draw(screenshot)
    found_text = []
    
    n_boxes = len(data['text'])
    for i in range(n_boxes):
        text = data['text'][i].strip()
        conf = int(data['conf'][i])
        
        if text and conf > 40: # Low threshold to see everything
            found_text.append(f"'{text}' (Conf: {conf})")
            
            x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
            draw.rectangle([x, y, x + w, y + h], outline="red", width=2)
            draw.text((x, y - 10), text, fill="red")

    # Save debug image
    output_filename = "ocr_debug_sample.png"
    screenshot.save(output_filename)
    print(f"Saved debug image to {output_filename}")
    
    print("\n--- Detected Text ---")
    print("\n".join(found_text))
    print("---------------------")

if __name__ == "__main__":
    debug_ocr()
