import json

def analyze_y(path, target_y, tolerance=20):
    with open(path, 'r') as f:
        segments = json.load(f)
        
    on_line = [s for s in segments if abs(s['box'][1] - target_y) < tolerance]
    on_line.sort(key=lambda s: s['box'][0])
    
    print(f"Segments near Y={target_y}:")
    for s in on_line:
        print(f"  {s['text']} at {s['box']} conf={s['conf']}")

if __name__ == "__main__":
    analyze_y("all_segments_verify.json", 143)
