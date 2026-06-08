"""Phone Link call test - proper UIA path."""
import sys, io, os, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pyautogui
import uiautomation as auto

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.03

def screenshot(name):
    os.makedirs("C:/Users/ggg/projects/auto-pickup/test_steps", exist_ok=True)
    path = f"C:/Users/ggg/projects/auto-pickup/test_steps/{name}.png"
    pyautogui.screenshot(path)
    print(f"Screenshot: {name}")

# Step 1: Activate Phone Link
print("Step 1: Win+7")
pyautogui.hotkey("win", "7")
time.sleep(3)
screenshot("v2_01_win7")

# Step 2: Find Phone Link and dialer
print("Step 2: Find dialer elements via UIA")
pl = auto.WindowControl(searchDepth=1, ClassName="WinUIDesktopWin32WindowClass")
print(f"  Phone Link: {pl.Name}")

# Find the search box directly - it's a top-level child of the window
search_box = pl.EditControl(AutoId="TextBox", searchDepth=10)
call_btn = pl.ButtonControl(AutoId="ButtonCall", searchDepth=10)
dialer_grid = pl.GroupControl(AutoId="DialPaneGrid", searchDepth=10)

print(f"  DialPaneGrid exists: {dialer_grid.Exists(2)}")
print(f"  TextBox exists: {search_box.Exists(2)}")
print(f"  ButtonCall exists: {call_btn.Exists(2)}")

if not dialer_grid.Exists(2):
    print("ERROR: Dialer not visible. Need to open it first.")
    # Try clicking the dial pad button or looking for it
    sys.exit(1)

# Step 3: Click search box and type number
print("Step 3: Click search box")
rect = search_box.BoundingRectangle
cx = (rect.left + rect.right) // 2
cy = (rect.top + rect.bottom) // 2
print(f"  Search box at ({cx},{cy})")
pyautogui.click(cx, cy)
time.sleep(0.5)

# Clear and type
pyautogui.hotkey("ctrl", "a")
time.sleep(0.1)
pyautogui.press("delete")
time.sleep(0.1)
print("Step 4: Typing number")
pyautogui.write("01280043725", interval=0.05)
time.sleep(1)
screenshot("v2_02_number_typed")

# Step 5: Click Call button
print("Step 5: Click Call button")
rect = call_btn.BoundingRectangle
cx = (rect.left + rect.right) // 2
cy = (rect.top + rect.bottom) // 2
print(f"  Call button at ({cx},{cy})")
pyautogui.click(cx, cy)
time.sleep(3)
screenshot("v2_03_after_call")

# Step 6: Verify
end_call = pl.ButtonControl(AutoId="EndCallButton", searchDepth=10)
if end_call.Exists(3):
    print("SUCCESS: Call is active!")
else:
    print("FAIL: No active call detected")
screenshot("v2_04_final")
print("Done")
