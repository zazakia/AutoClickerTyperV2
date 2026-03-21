import pygetwindow as gw

def audit_windows():
    print(f"{'Index':<5} {'Title':<60} {'Hex':<40} {'Box':<20} {'Visible':<10}")
    print("-" * 150)
    for i, w in enumerate(gw.getAllWindows()):
        try:
            h = w.title.encode('utf-8').hex()
        except:
            h = "N/A"
        print(f"{i:<5} {str(w.title):<60} {h:<40} {str((w.left, w.top, w.width, w.height)):<20} {w.visible:<10}")

if __name__ == "__main__":
    audit_windows()
