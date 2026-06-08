"""
Phone Link dialer v4 — clear field, scroll dialer, full sequence.
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
    user32 = ctypes.windll.user32
    user32.keybd_event(0, 0, 0, 0)
    user32.keybd_event(0, 0, KEYEVENTF_KEYUP, 0)
    time.sleep(0.3)


def find_phone_link():
    for child in auto.GetRootControl().GetChildren():
        if "phone link" in (child.Name or "").lower():
            return child
    return None


def bring_to_foreground(window):
    hwnd = window.NativeWindowHandle
    keybd_null()
    ctypes.windll.user32.ShowWindow(hwnd, 9)
    time.sleep(0.3)
    keybd_null()
    ctypes.windll.user32.SwitchToThisWindow(hwnd, True)
    time.sleep(0.5)


def find_control_by_automation_id(root, aid, max_depth=6):
    queue = [(root, 0)]
    while queue:
        ctrl, d = queue.pop(0)
        if ctrl.AutomationId == aid:
            return ctrl
        if d < max_depth:
            try:
                for c in ctrl.GetChildren():
                    queue.append((c, d+1))
            except:
                pass
    return None


def clear_dialer(pl_window):
    """Clear any existing number in the dialer."""
    # Method 1: Click edit box, select all, delete
    edit = find_control_by_automation_id(pl_window, 'TextBox')
    if edit:
        rect = edit.BoundingRectangle
        if not (rect.left == 0 and rect.right == 0):
            cx = int((rect.left + rect.right) / 2)
            cy = int((rect.top + rect.bottom) / 2)
            pyautogui.click(cx, cy)
            time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            time.sleep(0.1)
            pyautogui.press("delete")
            time.sleep(0.2)
            print("[CLEAR] Cleared via TextBox delete")
            return
    
    # Method 2: Backspace multiple times
    pyautogui.press("backspace")
    time.sleep(0.1)
    print("[CLEAR] Sent backspace")


def scroll_dialer_down(pl_window):
    """Scroll the dialer ScrollViewer down to reveal row 4 and Call button."""
    # Find the DialPane ScrollViewer
    sv = find_control_by_automation_id(pl_window, 'DialPane')
    if sv:
        rect = sv.BoundingRectangle
        cx = int((rect.left + rect.right) / 2)
        cy = int((rect.top + rect.bottom) / 2)
        print(f"[SCROLL] Scrolling DialPane at ({cx},{cy})")
        # Click inside the scroll viewer first to focus it
        pyautogui.click(cx, cy)
        time.sleep(0.3)
        # Send PageDown or mouse wheel down
        pyautogui.scroll(-3, x=cx, y=cy)
        time.sleep(0.5)
        print("[SCROLL] Scrolled down")
    else:
        print("[SCROLL] DialPane not found, trying mouse wheel on keypad area")
        kp = find_control_by_automation_id(pl_window, 'Keypad')
        if kp:
            rect = kp.BoundingRectangle
            cx = int((rect.left + rect.right) / 2)
            cy = int((rect.top + rect.bottom) / 2)
            pyautogui.scroll(-3, x=cx, y=cy)
            time.sleep(0.5)


def type_number_in_edit(pl_window, phone):
    """Type number into the search/edit box via clipboard paste."""
    edit = find_control_by_automation_id(pl_window, 'TextBox')
    if not edit:
        print("[TYPE] TextBox not found!")
        return False
    
    rect = edit.BoundingRectangle
    cx = int((rect.left + rect.right) / 2)
    cy = int((rect.top + rect.bottom) / 2)
    
    print(f"[TYPE] Clicking EditControl at ({cx},{cy})")
    pyautogui.click(cx, cy)
    time.sleep(0.3)
    
    # Select all and paste
    import pyperclip
    pyperclip.copy(phone)
    time.sleep(0.15)
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.15)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.5)
    print(f"[TYPE] Pasted: {phone}")
    return True


def click_call_button_visual(pl_window):
    """
    Find Call button via UIA. If 0-size, calculate its expected position
    based on the keypad layout and click there.
    """
    btn = find_control_by_automation_id(pl_window, 'ButtonCall')
    
    if btn:
        rect = btn.BoundingRectangle
        if not (rect.left == 0 and rect.right == 0):
            cx = int((rect.left + rect.right) / 2)
            cy = int((rect.top + rect.bottom) / 2)
            print(f"[CALL] Clicking visible Call button at ({cx},{cy})")
            pyautogui.click(cx, cy)
            time.sleep(0.5)
            return
    
    # Call button is virtual — estimate position from keypad layout
    # Keypad: [549,510,809,670], 3 cols, Call button is typically
    # centered below row 4, spanning all 3 columns
    kp = find_control_by_automation_id(pl_window, 'Keypad')
    if kp:
        rect = kp.BoundingRectangle
        # Estimate: Call button center = keypad horizontal center,
        # ~50px below keypad bottom
        cx = int((rect.left + rect.right) / 2)
        cy = rect.bottom + 45  # below the 7-8-9 row
        print(f"[CALL] Estimated Call button at ({cx},{cy})")
        pyautogui.click(cx, cy)
        time.sleep(0.5)
    else:
        print("[CALL] Trying Enter key as fallback")
        pyautogui.press("enter")
        time.sleep(0.5)


# ════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════

def main():
    global step
    print("=" * 60)
    print(f"Phone Link Dialer v4 — phone: {PHONE}")
    print("=" * 60)

    screenshot("baseline")

    keybd_null()
    screenshot("keybd_null")

    pl = find_phone_link()
    if not pl:
        print("[FAIL] No Phone Link!")
        return False
    print(f"[FIND] HWND={pl.NativeWindowHandle}")
    screenshot("found_pl")

    bring_to_foreground(pl)
    screenshot("foreground")

    # Ctrl+3 → Calls tab
    print("[TAB] Ctrl+3")
    pyautogui.hotkey("ctrl", "3")
    time.sleep(1.5)
    screenshot("calls_tab")

    # Clear any existing number
    print("[CLEAR] Clearing dialer...")
    clear_dialer(pl)
    screenshot("cleared")

    # Type number into edit box
    print("[TYPE] Typing number...")
    type_number_in_edit(pl, PHONE)
    screenshot("typed")

    # Scroll down to reveal Call button
    print("[SCROLL] Scrolling dialer...")
    scroll_dialer_down(pl)
    screenshot("scrolled")

    # Re-check Call button coordinates after scroll
    btn = find_control_by_automation_id(pl, 'ButtonCall')
    if btn:
        r = btn.BoundingRectangle
        print(f"[INFO] After scroll, Call button rect=[{r.left},{r.top},{r.right},{r.bottom}]")

    # Click Call button
    print("[CALL] Clicking call...")
    click_call_button_visual(pl)
    screenshot("call_pressed")

    time.sleep(2)
    screenshot("final")
    
    print(f"\nDONE — {step} screenshots saved")
    return True


if __name__ == "__main__":
    try:
        ok = main()
        sys.exit(0 if ok else 1)
    except Exception as e:
        print(f"\n[CRASH] {e}")
        import traceback
        traceback.print_exc()
        screenshot("crash")
        sys.exit(1)
