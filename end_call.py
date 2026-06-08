import uiautomation as auto
import pyautogui

pl = auto.WindowControl(searchDepth=1, ClassName="WinUIDesktopWin32WindowClass")
btn = pl.ButtonControl(AutoId="EndCallButton")
rect = btn.BoundingRectangle
cx = (rect.left + rect.right) // 2
cy = (rect.top + rect.bottom) // 2
print(f"End call at ({cx},{cy})")
pyautogui.click(cx, cy)
print("Done")
