import cv2
import numpy as np

def create_template(image_path, x, y, w, h, output_path):
    img = cv2.imread(image_path)
    if img is None:
        print("Image not found.")
        return
    template = img[y:y+h, x:x+w]
    cv2.imwrite(output_path, template)
    print(f"Template saved to {output_path}")

if __name__ == "__main__":
    # Based on list_line_objects.py: X=258 Y=143 W=24 H=24
    # We might want to be slightly more precise or pad it.
    create_template("debug_manager_crop.png", 258, 143, 24, 24, "bell_icon.png")
