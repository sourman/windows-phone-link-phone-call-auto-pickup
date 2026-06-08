import pyautogui
import time
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import uiautomation as auto

pyautogui.FAILSAFE = False
pyautogui.moveTo(500, 400)
time.sleep(0.5)
pyautogui.FAILSAFE = True

# Win+7 to activate Phone Link
pyautogui.hotkey('win', '7')
time.sleep(8)

# Check windows
for c in auto.GetRootControl().GetChildren():
    name = (c.Name or "").replace('\u200e', '')[:80]
    cls = c.ClassName or ""
    print(f"{c.ControlTypeName} | Name='{name}' | Class='{cls}'")
