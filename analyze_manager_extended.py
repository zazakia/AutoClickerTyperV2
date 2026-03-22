import json

def find_target_and_nearby_extended(path, target_text):
    with open(path, 'r') as f:
        segments = json.load(f)
        
    targets = [s for s in segments if target_text.lower() in s['text'].lower()]
    if not targets:
        print(f"Target '{target_text}' not found.")
        return
        
    for t in targets:
        print(f"\nTarget: '{t['text']}' at ({t['x']}, {t['y']}, {t['w']}, {t['h']})")
        # Find everything on the same line or slightly below
        nearby = [s for s in segments if abs(s['y'] - t['y']) < 50]
        # Sort by X
        nearby.sort(key=lambda s: s['x'])
        
        for s in nearby:
            dist = s['x'] - (t['x'] + t['w'])
            print(f"  [{s['text']}] at x={s['x']} y={s['y']} w={s['w']} h={s['h']} Dist: {dist}")

if __name__ == "__main__":
    find_target_and_nearby_extended("all_segments_manager.json", "Debugging")
