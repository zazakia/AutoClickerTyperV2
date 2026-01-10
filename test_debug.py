import subprocess
import time
import sys
import pygetwindow as gw

# Unbuffered output
sys.stdout.reconfigure(line_buffering=True)

print("DEBUG: Launching Target Window...")
proc = subprocess.Popen([sys.executable, "target_window.py"])

print("DEBUG: Waiting 3s...")
time.sleep(3)

print("DEBUG: Listing Windows...")
titles = gw.getAllTitles()
print(f"TITLES: {titles}")

if "Target Window" in titles:
    print("SUCCESS: Target Window found.")
else:
    print("FAIL: Target Window NOT found.")

proc.terminate()
