"""
Phone Link dialer v7 — CLICK-based foreground (no more Win32 FG hacks).
- Click PL title bar to bring it forward (real mouse = always works)
- Clear accumulator
- Type number
- UIA .Click() on Call button
"""
import ctypes
import sys
import time
from pathlib import Path
from collections import deque

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


def find_pl():
    for c in auto.GetRootControl().GetChildren():
        if "phone link" in (c.Name or "").lower():
            return c
    return None


def find_by_aid(root, aid, max_depth=6):
    q = deque([(root, 0)])
    while q:
        ctrl, d = q.popleft()
        if ctrl.AutomationId == aid:
            return ctrl
        if d < max_depth:
            try:
                for c in ctrl.GetChildren():
                    q.append((c, d+1))
            except:
                pass
    return None


def bring_pl_to_front_click(pl_window):
    """
    Bring PL to front by clicking its title bar area.
    Real mouse clicks ALWAYS work for focus stealing.
    """
    rect = pl_window.BoundingRectangle
    # Click near top-center of window (title bar area)
    # Title bar is roughly top 30-35 pixels of the window
    cx = int(rect.left + (rect.right - rect.left) / 2)
    cy = int(rect.top + 15)  # well within title bar
    
    print(f"[CLICK-FG] Clicking title bar at ({cx},{cy})")
    print(f"[CLICK-FG] Window rect: [{rect.left},{rect.top},{rect.right},{rect.bottom}]")
    
    pyautogui.click(cx, cy)
    time.sleep(0.8)
    
    # Verify
    fg = ctypes.windll.user32.GetForegroundWindow()
    match = fg == pl_window.NativeWindowHandle
    print(f"[CLICK-FG] FG HWND={fg} (PL={pl_window.NativeWindowHandle}, match={match})")
    
    if not match:
        # Try clicking again, slightly lower (in case title bar is custom/non-client)
        cy2 = int(rect.top + 25)
        print(f"[CLICK-FG] Retry at ({cx},{cy2})")
        pyautogui.click(cx, cy2)
        time.sleep(0.8)
        fg2 = ctypes.windll.user32.GetForegroundWindow()
        match2 = fg2 == pl_window.NativeWindowHandle
        print(f"[CLICK-FG] Retry FG HWND={fg2} (match={match2})")
        
        if not match2:
            # Nuclear option: double-click
            print("[CLICK-FG] Double-click attempt...")
            pyautogui.doubleClick(cx, cy)
            time.sleep(0.8)


def clear_accumulator(pl):
    """Clear digits from dialer."""
    edit = find_by_aid(pl, 'TextBox')
    if edit:
        rect = edit.BoundingRectangle
        if rect.left != 0 or rect.right != 0:
            cx = int((rect.left + rect.right) / 2)
            cy = int((rect.top + rect.bottom) / 2)
            pyautogui.click(cx, cy)
            time.sleep(0.3)
    
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.15)
    for _ in range(20):
        pyautogui.press("backspace")
        time.sleep(0.02)
    time.sleep(0.3)
    print("[CLEAR] Done")


def type_number(edit_ctrl, phone):
    """Type phone number digit by digit."""
    rect = edit_ctrl.BoundingRectangle
    cx = int((rect.left + rect.right) / 2)
    cy = int((rect.top + rect.bottom) / 2)
    
    print(f"[TYPE] Clicking edit at ({cx},{cy})")
    pyautogui.click(cx, cy)
    time.sleep(0.5)
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.1)
    
    print(f"[TYPE] Typing: {phone}")
    for digit in phone:
        pyautogui.press(digit)
        time.sleep(0.06)
    time.sleep(0.5)


def uia_click_call(pl):
    """UIA .Click() on ButtonCall."""
    btn = find_by_aid(pl, 'ButtonCall')
    if not btn:
        print("[CALL] ButtonCall NOT found!")
        return False
    
    r = btn.BoundingRectangle
    print(f"[CALL] '{btn.Name}' rect=[{r.left},{r.top},{r.right},{r.bottom}]")
    
    try:
        btn.Click()
        print("[CALL] UIA .Click() succeeded!")
        return True
    except Exception as e:
        print(f"[CALL] .Click() error: {e}")
        try:
            btn.GetInvokePattern().Invoke()
            print("[CALL] Invoke() succeeded!")
            return True
        except Exception as e2:
            print(f"[CALL] Invoke() error: {e2}")
            return False


def main():
    global step
    print("=" * 60)
    print(f"Phone Link Dialer v7 (click-FG) - phone: {PHONE}")
    print("=" * 60)

    screenshot("01_baseline")

    # Find PL
    pl = find_pl()
    if not pl:
        print("[FAIL] No PL")
        return False
    hwnd = pl.NativeWindowHandle
    print(f"[FIND] PL HWND={hwnd}")

    # Click title bar to bring to front
    print("\n[FG] Click-based foreground...")
    bring_pl_to_front_click(pl)
    screenshot("02_fg")

    # Verify
    fg = ctypes.windll.user32.GetForegroundWindow()
    print(f"[CHECK] FG={fg} PL={hwnd} match={fg==hwnd}")

    # Ctrl+3 -> Calls tab
    print("\n[TAB] Ctrl+3")
    pyautogui.hotkey("ctrl", "3")
    time.sleep(1.5)
    screenshot("03_calls")

    # Clear
    clear_accumulator(pl)
    screenshot("04_cleared")

    # Type
    edit = find_by_aid(pl, 'TextBox')
    if not edit:
        print("[FAIL] No TextBox")
        screenshot("FAIL_noedit")
        return False
    
    type_number(edit, PHONE)
    screenshot("05_typed")

    # Call via UIA
    print("\n[CALL] UIA Click...")
    uia_click_call(pl)
    screenshot("06_call")

    time.sleep(3)
    screenshot("07_final")

    print(f"\nDONE - {step} screenshots")


if __name__ == "__main__":
    try:
        ok = main()
        sys.exit(0 if ok else 1)
    except Exception as e:
        print(f"\n[CRASH] {e}")
        import traceback
        traceback.print_exc()
        screenshot("CRASH")
        sys.exit(1)
