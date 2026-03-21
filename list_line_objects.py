import json

def list_line_objects(path, y_coord, tolerance=20):
    with open(path, 'r') as f:
        segments = json.load(f)
    on_line = [s for s in segments if abs(s['y'] - y_coord) < tolerance]
    on_line.sort(key=lambda s: s['x'])
    for s in on_line:
        print(f"X={s['x']}\tY={s['y']}\tW={s['w']}\tH={s['h']}\tTEXT='{s['text']}'\tCONF={s['conf']}")

if __name__ == "__main__":
    list_line_objects("all_segments_manager.json", 143)
