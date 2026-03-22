import json

def find_target_and_nearby(path, target_text):
    with open(path, 'r') as f:
        segments = json.load(f)
        
    targets = [s for s in segments if target_text.lower() in s['text'].lower()]
    if not targets:
        print(f"Target '{target_text}' not found.")
        return
        
    for t in targets:
        print(f"\nTarget: '{t['text']}' at ({t['x']}, {t['y']}, {t['w']}, {t['h']})")
        # Find everything on the same line
        same_line = [s for s in segments if abs(s['y'] - t['y']) < 30 and s != t]
        for s in same_line:
            dist = t['x'] - (s['x'] + s['w']) if s['x'] < t['x'] else s['x'] - (t['x'] + t['w'])
            side = "LEFT" if s['x'] < t['x'] else "RIGHT"
            print(f"  Nearby: '{s['text']}' at ({s['x']}, {s['y']}) Dist: {dist} Side: {side}")

if __name__ == "__main__":
    find_target_and_nearby("all_segments_manager.json", "Debugging")
