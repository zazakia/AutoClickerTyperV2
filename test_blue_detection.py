"""
Quick test script to verify blue button detection is working.
This creates a simple test window with blue and non-blue buttons to verify filtering.
"""
import cv2
import numpy as np
from PIL import Image
import config
from core.ocr import detect_blue_regions, is_on_blue_background

def test_blue_detection():
    """Test the blue region detection with a synthetic image."""
    print("Testing Blue Button Detection...")
    print(f"Color filter enabled: {config.ENABLE_COLOR_FILTER}")
    print(f"HSV Lower: {config.BLUE_HSV_LOWER}")
    print(f"HSV Upper: {config.BLUE_HSV_UPPER}")
    print(f"Overlap threshold: {config.COLOR_OVERLAP_THRESHOLD}")
    
    # Create a test image with blue and red regions
    test_img = np.zeros((300, 400, 3), dtype=np.uint8)
    
    # Blue button (left side)
    cv2.rectangle(test_img, (50, 100), (150, 150), (255, 0, 0), -1)  # BGR: Blue
    cv2.putText(test_img, "Accept", (60, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    # Red button (right side)
    cv2.rectangle(test_img, (250, 100), (350, 150), (0, 0, 255), -1)  # BGR: Red
    cv2.putText(test_img, "Accept", (260, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    # Convert to PIL Image
    test_pil = Image.fromarray(cv2.cvtColor(test_img, cv2.COLOR_BGR2RGB))
    
    # Detect blue regions
    blue_mask = detect_blue_regions(test_pil)
    
    if blue_mask is not None:
        print("\n✓ Blue region detection executed successfully")
        
        # Test blue button region
        blue_box = (50, 100, 100, 50)
        is_blue = is_on_blue_background(blue_box, blue_mask, (0, 0))
        print(f"Blue button region detected as blue: {is_blue} {'✓' if is_blue else '✗'}")
        
        # Test red button region
        red_box = (250, 100, 100, 50)
        is_blue_red = is_on_blue_background(red_box, blue_mask, (0, 0))
        print(f"Red button region detected as blue: {is_blue_red} {'✓' if not is_blue_red else '✗'}")
        
        # Save visualization
        cv2.imwrite('test_image.png', test_img)
        cv2.imwrite('blue_mask.png', blue_mask)
        print("\n✓ Test images saved: test_image.png, blue_mask.png")
        
        if is_blue and not is_blue_red:
            print("\n✅ PASS: Blue detection is working correctly!")
            return True
        else:
            print("\n❌ FAIL: Blue detection is not filtering correctly")
            return False
    else:
        print("\n⚠ Color filtering is disabled")
        return False

if __name__ == "__main__":
    test_blue_detection()
