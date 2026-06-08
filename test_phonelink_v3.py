"""
Phone Link dialer v3 — UIA button clicks for dialing.
Instead of pasting into search box, click actual keypad buttons via UIA.
This reveals the Call button naturally.
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
    """BFS find control by AutomationId."""
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


def click_uia_button(ctrl):
    """Click a UIA button control at its center coordinates."""
    rect = ctrl.BoundingRectangle
    cx = int((rect.left + rect.right) / 2)
    cy = int((rect.top + rect.bottom) / 2)
    
    if rect.left == 0 and rect.right == 0:
        print(f"[BTN] Virtual button '{ctrl.Name}' — skipping (0-size)")
        return False
    
    print(f"[BTN] Clicking '{ctrl.Name}' at ({cx},{cy})")
    pyautogui.click(cx, cy)
    time.sleep(0.15)
    return True


def dial_number_via_keypad(pl_window, phone):
    """
    Dial by clicking individual keypad buttons via UIA.
    This populates the accumulator display and reveals the Call button.
    """
    # Map digits to their UIA AutomationIds
    btn_map = {
        '1': 'Button1', '2': 'Button2', '3': 'Button3',
        '4': 'Button4', '5': 'Button5', '6': 'Button6',
        '7': 'Button7', '8': 'Button8', '9': 'Button9',
        '0': 'Button0',
    }
    
    clicked_any = False
    for digit in phone:
        if digit not in btn_map:
            continue
        aid = btn_map[digit]
        btn = find_control_by_automation_id(pl_window, aid)
        if btn:
            clicked = click_uia_button(btn)
            if clicked:
                clicked_any = True
        else:
            print(f"[DIAL] Button '{aid}' not found for digit '{digit}'")
        time.sleep(0.1)
    
    return clicked_any


def click_call_button(pl_window):
    """Find and click the Call button."""
    btn = find_control_by_automation_id(pl_window, 'ButtonCall')
    if btn:
        rect = btn.BoundingRectangle
        if rect.left == 0 and rect.right == 0:
            # Still virtual — try scrolling or use Enter
            print("[CALL] Call button still virtual, trying Enter...")
            pyautogui.press("enter")
            time.sleep(0.5)
            return
        
        cx = int((rect.left + rect.right) / 2)
        cy = int((rect.top + rect.bottom) / 2)
        print(f"[CALL] Clicking Call at ({cx},{cy})")
        pyautogui.click(cx, cy)
        time.sleep(0.5)
    else:
        print("[CALL] Not found, trying Enter")
        pyautogui.press("enter")
        time.sleep(0.5)


# ════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════

def main():
    global step
    print("=" * 60)
    print(f"Phone Link Dialer v3 (UIA keypad) — phone: {PHONE}")
    print("=" * 60)

    screenshot("baseline")

    keybd_null()
    screenshot("keybd_null")

    pl = find_phone_link()
    if not pl:
        print("[FAIL] No Phone Link!")
        screenshot("fail_nopl")
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

    # Click each digit on the keypad
    print(f"[DIAL] Typing {PHONE} via UIA keypad buttons...")
    dial_number_via_keypad(pl, PHONE)
    screenshot("dialed_number")

    # Now check if Call button has real coordinates
    print("[CALL] Looking for Call button...")
    click_call_button(pl)
    screenshot("call_pressed")

    # Wait a moment then final screenshot
    time.sleep(2)
    screenshot("final_state")

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
