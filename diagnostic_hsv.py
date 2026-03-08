import cv2
import numpy as np
from PIL import Image
import json

def diagnostic_hsv(image_path):
    print(f"Analyzing {image_path}...")
    img = cv2.imread(image_path)
    if img is None:
        print("Failed to load image.")
        return
        
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    # Check common ranges
    ranges = {
        "Blue": ([100, 50, 50], [130, 255, 255]),
        "Yellow/Gold": ([20, 100, 100], [30, 255, 255]),
        "White/Bright": ([0, 0, 200], [180, 30, 255]),
        "Grey": ([0, 0, 40], [180, 50, 200])
    }
    
    results = {}
    for name, (lower, upper) in ranges.items():
        mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
        count = cv2.countNonZero(mask)
        results[name] = count
        print(f"{name} pixels: {count}")
        
    # Find average HSV in segments to detect "unusual" colors
    # We'll just save a visualization of the HSV mask for the user-provided colors
    # But for us, let's try a Very Broad Neutral range
    
if __name__ == "__main__":
    diagnostic_hsv("debug_manager_crop.png")
