"""
Phone Link dialer v2 — pure Python, UIA-driven coordinates.
Screenshots at each step.
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
    print("[KEYBD] Null keystroke sent")
    time.sleep(0.3)


def find_phone_link():
    for child in auto.GetRootControl().GetChildren():
        if "phone link" in (child.Name or "").lower():
            return child
    return None


def bring_to_foreground(window):
    hwnd = window.NativeWindowHandle
    keybd_null()
    ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    time.sleep(0.3)
    keybd_null()
    ctypes.windll.user32.SwitchToThisWindow(hwnd, True)
    time.sleep(0.5)
    print("[FG] Foreground activation done")


def find_dial_edit_control(window):
    """Find the 'Search your contacts' EditControl inside the Dialer."""
    def find_dialer(ctrl, depth=0):
        aid = ctrl.AutomationId or ""
        if aid == "DialPaneGrid":
            return ctrl
        if depth < 5:
            try:
                for c in ctrl.GetChildren():
                    r = find_dialer(c, depth+1)
                    if r:
                        return r
            except:
                pass
        return None
    
    def find_edit(ctrl, depth=0):
        ct = ctrl.ControlTypeName or ""
        if ct == "EditControl" and ctrl.AutomationId == "TextBox":
            return ctrl
        if depth < 4:
            try:
                for c in ctrl.GetChildren():
                    r = find_edit(c, depth+1)
                    if r:
                        return r
            except:
                pass
        return None
    
    dialer = find_dialer(window)
    if not dialer:
        return None
    return find_edit(dialer)


def click_and_type(edit_ctrl, phone):
    """Click the edit control center, then paste the number."""
    rect = edit_ctrl.BoundingRectangle
    cx = int((rect.left + rect.right) / 2)
    cy = int((rect.top + rect.bottom) / 2)
    
    print(f"[CLICK] EditControl center=({cx},{cy}) rect=[{rect.left},{rect.top},{rect.right},{rect.bottom}]")
    pyautogui.click(cx, cy)
    time.sleep(0.5)
    
    # Paste via clipboard
    import pyperclip
    pyperclip.copy(phone)
    time.sleep(0.15)
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.15)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.5)
    print(f"[TYPE] Pasted: {phone}")


def find_and_click_call_button(window):
    """Find the Call button in the Keypad and click it."""
    def find_call(ctrl, depth=0):
        aid = ctrl.AutomationId or ""
        if aid == "ButtonCall":
            return ctrl
        if depth < 6:
            try:
                for c in ctrl.GetChildren():
                    r = find_call(c, depth+1)
                    if r:
                        return r
            except:
                pass
        return None
    
    btn = find_call(window)
    if btn:
        rect = btn.BoundingRectangle
        # If button is 0-sized, it's virtual/off-screen — use Enter instead
        if rect.left == 0 and rect.right == 0:
            print("[CALL] Button is virtual (0-size), using Enter key instead")
            pyautogui.press("enter")
        else:
            cx = int((rect.left + rect.right) / 2)
            cy = int((rect.top + rect.bottom) / 2)
            print(f"[CALL] Clicking Call button at ({cx},{cy})")
            pyautogui.click(cx, cy)
    else:
        print("[CALL] Call button not found via UIA, using Enter key")
        pyautogui.press("enter")
    time.sleep(0.5)


# ════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════

def main():
    global step
    print("=" * 60)
    print(f"Phone Link Dialer v2 — phone: {PHONE}")
    print("=" * 60)

    # Step 1: Baseline
    screenshot("baseline")

    # Step 2: Null keystroke
    keybd_null()
    screenshot("keybd_null")

    # Step 3: Find PL
    pl = find_phone_link()
    if not pl:
        print("[FAIL] No Phone Link!")
        screenshot("fail_nopl")
        return False
    print(f"[FIND] Phone Link HWND={pl.NativeWindowHandle}")
    screenshot("found_pl")

    # Step 4: Foreground
    bring_to_foreground(pl)
    screenshot("foreground")

    # Step 5: Ctrl+3 → Calls tab
    print("[TAB] Ctrl+3 for Calls")
    pyautogui.hotkey("ctrl", "3")
    time.sleep(1.5)
    screenshot("calls_tab")

    # Step 6: Find + click the EditControl via UIA
    print("[EDIT] Finding EditControl via UIA...")
    edit = find_dial_edit_control(pl)
    if not edit:
        print("[FAIL] No EditControl found!")
        screenshot("fail_noedit")
        return False
    click_and_type(edit, PHONE)
    screenshot("typed_number")

    # Step 7: Find + click Call button (or Enter)
    print("[CALL] Finding Call button...")
    find_and_click_call_button(pl)
    screenshot("call_pressed")

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
