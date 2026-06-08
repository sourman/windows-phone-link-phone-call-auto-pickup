"""Phone Link call - click by calculated coordinates based on window geometry."""
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

# Step 2: Get actual window rect from Win32 (not UIA)
pl = auto.WindowControl(searchDepth=1, ClassName="WinUIDesktopWin32WindowClass")
pl.SetFocus()
time.sleep(0.5)

# Use pyautogui to get window position by screenshot analysis
# Take screenshot first to see where things are
screenshot("v5_01_initial")

# Phone Link is maximized based on rect (-8,-8,1374,728)
# The dialer is on the RIGHT side of the window
# Window is ~1382px wide, ~736px tall
# Right panel (dialer) starts roughly at 60% of width

# Let me click the "Search your contacts" text field
# It should be in the right panel, roughly at these coordinates
# Based on the screenshots, the dialer area is on the right ~40% of the window
# Search box is at the top of the dialer area

# Window coordinates (maximized): left=-8, top=-8, right=1374, bottom=728
# Actual visible area: 0,0 to 1366,720 (1920-? actually let's check)
screen_w, screen_h = pyautogui.size()
print(f"Screen: {screen_w}x{screen_h}")

# From screenshots, the right panel dialer area is roughly:
# The dialer keypad is visible in the right portion
# Let me click just above the keypad buttons where the number display is

# Based on visual inspection: 
# Dialer keypad center is roughly at (1200, 550) 
# Number display is about 150px above keypad center
# Search "Search your contacts" is about 200px above keypad

# Try clicking the number display area (above keypad, right side)
click_x = 1200
click_y = 400
print(f"Clicking dialer display at ({click_x},{click_y})")
pyautogui.click(click_x, click_y)
time.sleep(0.5)
screenshot("v5_02_display_clicked")

# Type number
print("Typing number...")
pyautogui.write("01280043725", interval=0.08)
time.sleep(1)
screenshot("v5_03_typed")

# Check if number appeared - if not, try clicking different position
# The call button should be at bottom of keypad
click_x_call = 1250
click_y_call = 680
print(f"Clicking Call at ({click_x_call},{click_y_call})")
pyautogui.click(click_x_call, click_y_call)
time.sleep(4)
screenshot("v5_04_after_call")

print("Done - check screenshots")
