"""Phone Link call - coordinate-based with safety measures."""
import sys, io, os, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pyautogui

pyautogui.FAILSAFE = False  # Needed because UIA elements return 0,0 coords

def screenshot(name):
    os.makedirs("C:/Users/ggg/projects/auto-pickup/test_steps", exist_ok=True)
    path = f"C:/Users/ggg/projects/auto-pickup/test_steps/{name}.png"
    pyautogui.screenshot(path)
    print(f"Screenshot: {name}")

# Move mouse to center first
pyautogui.moveTo(640, 360)
time.sleep(0.3)

# Step 1: Activate Phone Link
print("Step 1: Win+7")
pyautogui.hotkey("win", "7")
time.sleep(3)
screenshot("v6_01_win7")

# Step 2: Click on "Search your contacts" field (right panel of Phone Link)
# From screenshot analysis: the search field is at top-right of the dialer
# Dialer is in the right ~40% of the window
print("Step 2: Click search field")
pyautogui.click(1170, 180)
time.sleep(0.5)
screenshot("v6_02_search_clicked")

# Step 3: Type number
print("Step 3: Type number")
pyautogui.write("01280043725", interval=0.08)
time.sleep(1)
screenshot("v6_03_typed")

# Step 4: Press Enter or click Call
print("Step 4: Press Enter to call")
pyautogui.press("enter")
time.sleep(4)
screenshot("v6_04_after_call")

print("Done")
