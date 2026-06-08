import uiautomation as auto
import pyautogui
import time

pl = auto.WindowControl(searchDepth=1, ClassName="WinUIDesktopWin32WindowClass")
btn = pl.ButtonControl(AutoId="EndCallButton")
rect = btn.BoundingRectangle
print(f"End call button rect: ({rect.left},{rect.top})-({rect.right},{rect.bottom})")
print(f"Phone Link window: {pl.BoundingRectangle}")

# Click the center of the button
cx = (rect.left + rect.right) // 2
cy = (rect.top + rect.bottom) // 2
print(f"Clicking ({cx},{cy})")
pyautogui.click(cx, cy)
time.sleep(2)

# Check if call ended
btn2 = pl.ButtonControl(AutoId="EndCallButton")
print(f"End call still exists: {btn2.Exists(1)}")
