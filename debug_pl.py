import uiautomation as auto
import pyautogui
import time

pl = auto.WindowControl(searchDepth=1, ClassName="WinUIDesktopWin32WindowClass")
rect = pl.BoundingRectangle
print(f"Phone Link rect: ({rect.left},{rect.top})-({rect.right},{rect.bottom})")

# Screenshot the area
ss = pyautogui.screenshot(r"C:\Users\ggg\projects\auto-pickup\debug_phonelink.png")
print("Screenshot taken")

# Try expanding first
expand = pl.ButtonControl(AutoId="_ExpandButton")
if expand.Exists(1):
    er = expand.BoundingRectangle
    cx = (er.left + er.right) // 2
    cy = (er.top + er.bottom) // 2
    print(f"Expand button at ({cx},{cy}), clicking...")
    pyautogui.click(cx, cy)
    time.sleep(2)

# Now try End call
btn = pl.ButtonControl(AutoId="EndCallButton")
if btn.Exists(1):
    br = btn.BoundingRectangle
    cx = (br.left + br.right) // 2
    cy = (br.top + br.bottom) // 2
    print(f"End call at ({cx},{cy}), clicking...")
    pyautogui.click(cx, cy)
    time.sleep(1)

ss2 = pyautogui.screenshot(r"C:\Users\ggg\projects\auto-pickup\debug_phonelink2.png")
print("Done")
