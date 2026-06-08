"""Step-by-step Phone Link call test with visual verification."""
import sys, io, os, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
import pyautogui
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.03

def screenshot(name):
    path = os.path.join(SCRIPT_DIR, "test_steps", f"{name}.png")
    os.makedirs(os.path.join(SCRIPT_DIR, "test_steps"), exist_ok=True)
    pyautogui.screenshot(path)
    print(f"Screenshot: {name}")
    return path

# Step 1: Activate Phone Link via Win+7
print("Step 1: Win+7 to activate Phone Link")
pyautogui.hotkey("win", "7")
time.sleep(3)
screenshot("01_after_win7")

# Step 2: Ctrl+3 to switch to Calls
print("Step 2: Ctrl+3 to switch to Calls")
pyautogui.hotkey("ctrl", "3")
time.sleep(2)
screenshot("02_after_ctrl3")

# Step 3: Type phone number
print("Step 3: Type phone number")
pyautogui.write("01280043725", interval=0.05)
time.sleep(1)
screenshot("03_after_typing")

# Step 4: Check UIA tree for Call button
import uiautomation as auto
pl = auto.WindowControl(searchDepth=1, ClassName="WinUIDesktopWin32WindowClass")
if pl.Exists(2):
    dialer = pl.GroupControl(AutoId="DialPaneGrid")
    if dialer.Exists(2):
        call_btn = dialer.ButtonControl(AutoId="ButtonCall")
        if call_btn.Exists(2):
            rect = call_btn.BoundingRectangle
            print(f"Step 4: Call button found at ({rect.left},{rect.top})-({rect.right},{rect.bottom})")
            # Click it
            cx = (rect.left + rect.right) // 2
            cy = (rect.top + rect.bottom) // 2
            print(f"Clicking ({cx},{cy})")
            pyautogui.click(cx, cy)
            time.sleep(2)
            screenshot("04_after_call_click")
        else:
            print("Step 4: Call button NOT found in UIA")
            # Try Enter
            print("Pressing Enter as fallback")
            pyautogui.press("enter")
            time.sleep(2)
            screenshot("04_after_enter")
    else:
        print("Step 4: Dialer not found")
        pyautogui.press("enter")
        time.sleep(2)
        screenshot("04_after_enter_fallback")
else:
    print("Step 4: Phone Link window not found")
    pyautogui.press("enter")
    time.sleep(2)
    screenshot("04_no_phonelink")

# Step 5: Check if call started
screenshot("05_final_state")

# Check for EndCall button
end_call = pl.ButtonControl(AutoId="EndCallButton") if pl.Exists(1) else None
if end_call and end_call.Exists(1):
    print("SUCCESS: Call is active (EndCall button found)")
else:
    print("FAIL: Call does not appear to be active")

print("Done")
