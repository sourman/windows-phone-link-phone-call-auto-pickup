"""
Phone Link dialer v5 — type digits as keystrokes (not paste).
This mimics actual user input and should activate the Call button.
"""
import ctypes
import sys
import time
from pathlib import Path

import pyautogui
import uiautomation as auto

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05

SCRIPT_DIR = Path(__file__).resolve().parent
SCREENSHOT_DIR = SCRIPT_DIR / "test_steps"
SCREENSHOT_DIR.mkdir(exist_ok=True)

PHONE = sys.argv[1] if len(sys.argv) > 1 else "01280043725"
step = 0


def screenshot(name):
    global step
    step += 1
    path = SCREENSHOT_DIR / f"step{step:02d}_{name}.png"
    img = pyautogui.screenshot()
    img.save(str(path))
    print(f"[STEP {step}] {path.name}")
    return path


def keybd_null():
    KEYEVENTF_KEYUP = 0x0002
    u = ctypes.windll.user32
    u.keybd_event(0, 0, 0, 0)
    u.keybd_event(0, 0, KEYEVENTF_KEYUP, 0)
    time.sleep(0.3)


def find_pl():
    for c in auto.GetRootControl().GetChildren():
        if "phone link" in (c.Name or "").lower():
            return c
    return None


def fg(window):
    hwnd = window.NativeWindowHandle
    keybd_null()
    ctypes.windll.user32.ShowWindow(hwnd, 9)
    time.sleep(0.3)
    keybd_null()
    ctypes.windll.user32.SwitchToThisWindow(hwnd, True)
    time.sleep(0.5)


def find_by_aid(root, aid, max_depth=6):
    q = [(root, 0)]
    while q:
        ctrl, d = q.pop(0)
        if ctrl.AutomationId == aid:
            return ctrl
        if d < max_depth:
            try:
                for c in ctrl.GetChildren():
                    q.append((c, d+1))
            except:
                pass
    return None


def main():
    global step
    print(f"=== v5 (keystroke dialing) — phone: {PHONE} ===")

    screenshot("01_baseline")
    
    keybd_null()
    screenshot("02_keybd")
    
    pl = find_pl()
    if not pl:
        print("[FAIL] No PL")
        return False
    print(f"[FIND] HWND={pl.NativeWindowHandle}")
    screenshot("03_found")
    
    fg(pl)
    screenshot("04_fg")
    
    # Ctrl+3 → Calls tab
    print("[TAB] Ctrl+3")
    pyautogui.hotkey("ctrl", "3")
    time.sleep(1.5)
    screenshot("05_calls")
    
    # Click the EditControl (search/number input)
    edit = find_by_aid(pl, 'TextBox')
    if not edit:
        print("[FAIL] No TextBox")
        return False
    
    rect = edit.BoundingRectangle
    cx = int((rect.left + rect.right) / 2)
    cy = int((rect.top + rect.bottom) / 2)
    print(f"[CLICK] EditControl at ({cx},{cy})")
    pyautogui.click(cx, cy)
    time.sleep(0.5)
    screenshot("06_focused")
    
    # Clear any existing text first
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.1)
    pyautogui.press("delete")
    time.sleep(0.3)
    screenshot("07_cleared")
    
    # TYPE each digit as individual keystrokes (like a real user)
    print(f"[TYPE] Typing {PHONE} digit by digit...")
    for i, digit in enumerate(PHONE):
        pyautogui.press(digit)
        time.sleep(0.08)  # small delay between digits
        if (i + 1) % 3 == 0:
            time.sleep(0.15)  # slightly longer every 3 digits
            # Take a screenshot every few digits to watch progress
            if (i + 1) % 5 == 0:
                pass  # don't screenshot every digit, too noisy
    
    time.sleep(0.5)
    screenshot("08_typed_digits")
    
    # Now dump UIA again to see if Call button appeared
    btn = find_by_aid(pl, 'ButtonCall')
    if btn:
        r = btn.BoundingRectangle
        print(f"[CALL] ButtonCall rect=[{r.left},{r.top},{r.right},{r.bottom}]")
        
        if r.left != 0 or r.right != 0:
            bcx = int((r.left + r.right) / 2)
            bcy = int((r.top + r.bottom) / 2)
            print(f"[CALL] Clicking at ({bcx},{bcy})")
            pyautogui.click(bcx, bcy)
        else:
            # Still virtual — scan for green pixels now that we've typed
            print("[CALL] Button still virtual, scanning for green...")
            from PIL import Image
            img = pyautogui.screenshot()
            pl_img = img.crop((264, 89, 1053, 678))
            px = pl_img.load()
            w2, h2 = pl_img.size
            
            greens = []
            for yy in range(h2):
                for xx in range(w2):
                    rr, gg, bb = px[xx, yy][:3]
                    if gg > 120 and gg > rr * 2 and gg > bb * 1.5:
                        greens.append((xx, yy))
            
            if greens:
                ax = sum(g[0] for g in greens) / len(greens)
                ay = sum(g[1] for g in greens) / len(greens)
                scx = int(264 + ax)
                scy = int(89 + ay)
                print(f"[CALL] Green found! Clicking ({scx},{scy}) — {len(greens)} green px")
                pyautogui.click(scx, scy)
            else:
                print("[CALL] No green found, trying Enter")
                pyautogui.press("enter")
    else:
        print("[CALL] No ButtonCall found, trying Enter")
        pyautogui.press("enter")
    
    time.sleep(0.5)
    screenshot("09_call")
    
    time.sleep(2)
    screenshot("10_final")
    
    print(f"DONE — {step} steps")
    return True


if __name__ == "__main__":
    try:
        ok = main()
        sys.exit(0 if ok else 1)
    except Exception as e:
        print(f"[CRASH] {e}")
        import traceback
        traceback.print_exc()
        screenshot("crash")
        sys.exit(1)
