import json

def find_nearby_text(results_path, anchor_keyword):
    with open(results_path, 'r') as f:
        results = json.load(f)
        
    anchors = [r for r in results if anchor_keyword.lower() in r[0].lower()]
    print(f"Anchors found for '{anchor_keyword}': {len(anchors)}")
    
    for a_text, ax, ay, a_conf in anchors:
        print(f"\nAnchor: '{a_text}' at ({ax}, {ay})")
        # Find text on same line (y +/- 20)
        same_line = [r for r in results if abs(r[2] - ay) < 30 and r != [a_text, ax, ay, a_conf]]
        for t_text, tx, ty, t_conf in same_line:
            dist = ax - tx if tx < ax else tx - ax
            side = "LEFT" if tx < ax else "RIGHT"
            print(f"  Nearby: '{t_text}' at ({tx}, {ty}) Dist: {dist} Side: {side}")

if __name__ == "__main__":
    find_nearby_text("debug_ocr_results.json", "bell")
