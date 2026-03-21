import pygetwindow as gw

def check_window(title):
    wins = gw.getWindowsWithTitle(title)
    print(f"Windows with title '{title}':")
    for w in wins:
        print(f"  Title: '{w.title}'")
        print(f"  Box: {w.left}, {w.top}, {w.width}, {w.height}")
        print(f"  Visible: {w.visible}")
        print(f"  Minimized: {w.isMinimized}")
        print(f"  Maximized: {w.isMaximized}")

if __name__ == "__main__":
    check_window("Manager")
