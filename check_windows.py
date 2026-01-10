import pygetwindow as gw

def list_windows():
    with open("window_list.txt", "w", encoding="utf-8") as f:
        f.write("Listing all visible windows:\n")
        f.write("-" * 30 + "\n")
        for title in gw.getAllTitles():
            if title.strip():
                f.write(f"'{title}'\n")
        f.write("-" * 30 + "\n")

if __name__ == "__main__":
    list_windows()
