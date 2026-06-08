"""Phone Link call - click dialer display area and type via keypad."""
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
screenshot("v3_01_win7")

# Step 2: Get Phone Link window rect
pl = auto.WindowControl(searchDepth=1, ClassName="WinUIDesktopWin32WindowClass")
pl_rect = pl.BoundingRectangle
print(f"Phone Link rect: left={pl_rect.left} top={pl_rect.top} right={pl_rect.right} bottom={pl_rect.bottom}")

# Step 3: Get Call button position
call_btn = pl.ButtonControl(AutoId="ButtonCall", searchDepth=10)
print(f"ButtonCall exists: {call_btn.Exists(2)}")
if call_btn.Exists(2):
    cb_rect = call_btn.BoundingRectangle
    print(f"ButtonCall rect: left={cb_rect.left} top={cb_rect.top} right={cb_rect.right} bottom={cb_rect.bottom}")
    # The dialer display is directly above the keypad, which is above the call button
    # Keypad area: roughly from call_btn top up by ~200px
    # Display area: above keypad, roughly from call_btn top - 250 to call_btn top - 200

# Step 4: Find the DialPane - it should have a visible display area
dialer = pl.GroupControl(AutoId="DialPaneGrid", searchDepth=10)
if dialer.Exists(2):
    d_rect = dialer.BoundingRectangle
    print(f"Dialer rect: left={d_rect.left} top={d_rect.top} right={d_rect.right} bottom={d_rect.bottom}")

# Step 5: Find the keypad to calculate display position
keypad = pl.GroupControl(AutoId="Keypad", searchDepth=10)
if keypad.Exists(2):
    k_rect = keypad.BoundingRectangle
    print(f"Keypad rect: left={k_rect.left} top={k_rect.top} right={k_rect.right} bottom={k_rect.bottom}")
    # The display is above the keypad - click there
    display_y = k_rect.top - 30  # 30px above keypad
    display_x = (k_rect.left + k_rect.right) // 2
    print(f"Clicking display area at ({display_x},{display_y})")
    pyautogui.click(display_x, display_y)
    time.sleep(0.5)
    screenshot("v3_02_display_clicked")

    # Type the number
    print("Typing number...")
    pyautogui.write("01280043725", interval=0.08)
    time.sleep(1)
    screenshot("v3_03_number_typed")

# Step 6: Click Call button
if call_btn.Exists(2):
    cb_rect = call_btn.BoundingRectangle
    cx = (cb_rect.left + cb_rect.right) // 2
    cy = (cb_rect.top + cb_rect.bottom) // 2
    print(f"Clicking Call button at ({cx},{cy})")
    pyautogui.click(cx, cy)
    time.sleep(4)
    screenshot("v3_04_after_call")

    # Verify
    end_call = pl.ButtonControl(AutoId="EndCallButton", searchDepth=10)
    if end_call.Exists(3):
        print("SUCCESS: Call is active!")
    else:
        print("FAIL: No active call")

print("Done")
