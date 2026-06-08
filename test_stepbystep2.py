"""Step-by-step Phone Link call test - FIXED with UIA click on search box."""
import sys, io, os, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
import pyautogui
import uiautomation as auto

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.03

def screenshot(name):
    path = os.path.join(SCRIPT_DIR, "test_steps", f"{name}.png")
    os.makedirs(os.path.join(SCRIPT_DIR, "test_steps"), exist_ok=True)
    pyautogui.screenshot(path)
    print(f"Screenshot: {name}")

# Step 1: Activate Phone Link
print("Step 1: Win+7")
pyautogui.hotkey("win", "7")
time.sleep(3)
screenshot("fix_01_win7")

# Step 2: Find Phone Link via UIA
print("Step 2: Find Phone Link via UIA")
pl = auto.WindowControl(searchDepth=1, ClassName="WinUIDesktopWin32WindowClass")
print(f"  Found: {pl.Name}, rect: {pl.BoundingRectangle}")

# Step 3: Click Calls tab via UIA
print("Step 3: Click Calls tab via UIA")
nav = pl.CustomControl(AutoId="NavView")
calls_tab = nav.TabItemControl(AutoId="CallingNodeAutomationId")
if calls_tab.Exists(2):
    rect = calls_tab.BoundingRectangle
    cx = (rect.left + rect.right) // 2
    cy = (rect.top + rect.bottom) // 2
    print(f"  Calls tab at ({cx},{cy}), clicking")
    pyautogui.click(cx, cy)
    time.sleep(2)
else:
    print("  Calls tab not found, Ctrl+3 fallback")
    pyautogui.hotkey("ctrl", "3")
    time.sleep(2)
screenshot("fix_02_calls_tab")

# Step 4: Find and click the search box via UIA
print("Step 4: Click search box via UIA")
dialer = pl.GroupControl(AutoId="DialPaneGrid")
search = dialer.EditControl(AutoId="TextBox")
if search.Exists(2):
    rect = search.BoundingRectangle
    cx = (rect.left + rect.right) // 2
    cy = (rect.top + rect.bottom) // 2
    print(f"  Search box at ({cx},{cy}), clicking")
    pyautogui.click(cx, cy)
    time.sleep(0.5)
else:
    print("  Search box not found!")
screenshot("fix_03_search_clicked")

# Step 5: Type phone number
print("Step 5: Type phone number")
pyautogui.hotkey("ctrl", "a")
time.sleep(0.1)
pyautogui.press("delete")
time.sleep(0.1)
pyautogui.write("01280043725", interval=0.05)
time.sleep(1)
screenshot("fix_04_number_typed")

# Step 6: Click Call button via UIA
print("Step 6: Click Call button via UIA")
call_btn = dialer.ButtonControl(AutoId="ButtonCall")
if call_btn.Exists(2):
    rect = call_btn.BoundingRectangle
    cx = (rect.left + rect.right) // 2
    cy = (rect.top + rect.bottom) // 2
    print(f"  Call button at ({cx},{cy}), clicking")
    pyautogui.click(cx, cy)
else:
    print("  Call button not found, pressing Enter")
    pyautogui.press("enter")
time.sleep(3)
screenshot("fix_05_after_call")

# Step 7: Verify
end_call = pl.ButtonControl(AutoId="EndCallButton")
if end_call.Exists(2):
    print("SUCCESS: Call is active!")
else:
    print("FAIL: No active call detected")
    
print("Done")
