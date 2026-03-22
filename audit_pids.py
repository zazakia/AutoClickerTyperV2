import win32gui
import win32process

def audit_pids():
    def callback(hwnd, extra):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                print(f"HWND: {hwnd:<10} PID: {pid:<10} Title: {title}")
        return True

    print(f"{'HWND':<10} {'PID':<10} {'Title':<60}")
    print("-" * 100)
    win32gui.EnumWindows(callback, None)

if __name__ == "__main__":
    audit_pids()
