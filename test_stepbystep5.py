"""Phone Link call - force focus with window click, then use UIA SetValue."""
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
screenshot("v4_01_win7")

# Step 2: Click Phone Link title bar to ensure focus
pl = auto.WindowControl(searchDepth=1, ClassName="WinUIDesktopWin32WindowClass")
pl.SetFocus()
time.sleep(0.5)
print("SetFocus on Phone Link window")

# Step 3: Use UIA to find and click the search box via Invoke or Click
print("Step 3: Find search box via UIA and use SetValue")
# The EditControl with AutoId TextBox - try to set focus on it
search = pl.EditControl(AutoId="TextBox", searchDepth=15)
print(f"  TextBox Exists: {search.Exists(3)}")
if search.Exists(3):
    print(f"  TextBox Name: {search.Name}")
    print(f"  TextBox rect: {search.BoundingRectangle}")
    # Try GetClickablePoint
    try:
        point = search.GetClickablePoint()
        print(f"  ClickablePoint: {point}")
        if point and point[0] > 0 and point[1] > 0:
            pyautogui.click(point[0], point[1])
            time.sleep(0.5)
            screenshot("v4_02_search_clicked")
    except Exception as e:
        print(f"  GetClickablePoint error: {e}")

    # Try UIA SetValue
    try:
        search.SetValue("01280043725")
        print("  SetValue succeeded!")
        time.sleep(1)
        screenshot("v4_03_setvalue")
    except Exception as e:
        print(f"  SetValue error: {e}")

# Also try clicking the first contact from call history (0128 004 3725)
print("Step 4: Try clicking first call history entry")
history = pl.ListControl(AutoId="CallHistory", searchDepth=10)
if history.Exists(2):
    first_item = history.ListItemControl(searchDepth=1)
    if first_item.Exists(2):
        print(f"  First item: {first_item.Name}")
        try:
            point = first_item.GetClickablePoint()
            print(f"  ClickablePoint: {point}")
        except:
            pass
        rect = first_item.BoundingRectangle
        print(f"  rect: {rect}")
        # Double-click to call
        cx = (rect.left + rect.right) // 2
        cy = (rect.top + rect.bottom) // 2
        print(f"  Double-clicking at ({cx},{cy})")
        pyautogui.doubleClick(cx, cy)
        time.sleep(4)
        screenshot("v4_04_history_dblclick")
        
        # Verify
        end_call = pl.ButtonControl(AutoId="EndCallButton", searchDepth=10)
        if end_call.Exists(3):
            print("SUCCESS: Call active from history double-click!")
        else:
            print("No call from history double-click")

print("Done")
