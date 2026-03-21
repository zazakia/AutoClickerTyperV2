import json

def find_keywords(path, keywords):
    with open(path, 'r') as f:
        results = json.load(f)
    found = []
    for text, x, y, conf in results:
        for k in keywords:
            if k.lower() in text.lower():
                found.append((text, x, y, conf))
    return found

if __name__ == "__main__":
    print("Full Screen Results:")
    for r in find_keywords("debug_ocr_results.json", ["bell", "Debugging"]):
        print(r)
        
    print("\nManager Window Results:")
    for r in find_keywords("debug_manager_ocr.json", ["bell", "Debugging"]):
        print(r)
