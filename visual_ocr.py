import cv2
import json

def visualize_ocr(image_path, results_path, output_path):
    img = cv2.imread(image_path)
    if img is None:
        print("Image not found.")
        return
        
    with open(results_path, 'r') as f:
        results = json.load(f)
        
    for text, x, y, conf in results:
        # Assuming we don't have w, h in the json, we'll use a fixed size for visualization
        # Or better, I should have included w, h in the json earlier.
        cv2.rectangle(img, (x, y), (x + 50, y + 20), (0, 255, 0), 1)
        cv2.putText(img, text, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
    cv2.imwrite(output_path, img)
    print(f"Visualization saved to {output_path}")

if __name__ == "__main__":
    visualize_ocr("debug_current_full.png", "debug_ocr_results.json", "visual_ocr_debug.png")
