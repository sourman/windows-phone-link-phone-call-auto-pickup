"""
Stepped Phone Link dialer — pure Python, no AHK.
Screenshots at each step for visual verification.

Usage (from Windows Python):
    python test_phonelink_step.py [phone_number]

Steps:
  1. Screenshot baseline
  2. keybd_event null keystroke (foreground unlock)
  3. Find + activate Phone Link window
  4. Switch to Calls panel (Ctrl+3)
  5. Screenshot after switch
  6. Click dial pad / number input area
  7. Type phone number
  8. Screenshot before call
  9. Press Enter to call
  10. Final screenshot
"""

import ctypes
import ctypes.wintypes
import sys
import time
import subprocess
from pathlib import Path

import pyautogui

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05

SCRIPT_DIR = Path(__file__).resolve().parent
SCREENSHOT_DIR = SCRIPT_DIR / "test_steps"
SCREENSHOT_DIR.mkdir(exist_ok=True)

PHONE = sys.argv[1] if len(sys.argv) > 1 else "01280043725"

step = 0


def screenshot(name: str):
    """Take a numbered screenshot."""
    global step
    step += 1
    path = SCREENSHOT_DIR / f"step{step:02d}_{name}.png"
    # Use PowerShell GDI+ screenshot from python side
    try:
        import datetime
        ts = datetime.datetime.now().strftime("%H%M%S")
        # pyautogui screenshot
        img = pyautogui.screenshot()
        img.save(str(path))
        print(f"[STEP {step}] Screenshot saved: {path.name}")
    except Exception as e:
        print(f"[STEP {step}] Screenshot failed: {e}")
    return path


def keybd_null():
    """
    Send a null keystroke via keybd_event.
    This satisfies Windows' "calling process received last input event" condition,
    allowing SetForegroundWindow / SwitchToThisWindow to work from background processes.
    """
    KEYEVENTF_KEYUP = 0x0002
    user32 = ctypes.windll.user32
    user32.keybd_event(0, 0, 0, 0)          # key down
    user32.keybd_event(0, 0, KEYEVENTF_KEYUP, 0)  # key up
    print("[KEYBD] Null keystroke sent — foreground lock released")
    time.sleep(0.3)


def find_phone_link_window():
    """Find Phone Link main window using UIA or process enumeration."""
    import uiautomation as auto
    
    # Method 1: Search by window name
    for child in auto.GetRootControl().GetChildren():
        name = child.Name or ""
        cls = child.ClassName or ""
        if "phone link" in name.lower() or "phonelink" in name.lower() or cls == "PhoneLink":
            print(f"[FIND] Found by name: '{name}' class={cls}")
            return child
    
    # Method 2: Look for PhoneLinkHost or similar UWP window class
    for child in auto.GetRootControl().GetChildren():
        cls = child.ClassName or ""
        if "PhoneLink" in cls or "phone" in cls.lower():
            print(f"[FIND] Found by class: '{child.Name}' class={cls}")
            return child
    
    print("[FIND] Phone Link window not found via UIA")
    return None


def bring_to_foreground(window):
    """
    Bring a UIA window to foreground using keybd_event + SwitchToThisWindow technique.
    """
    hwnd = window.NativeWindowHandle
    print(f"[FG] Bringing window HWND={hwnd} to foreground")
    
    # 1. Null keystroke first
    keybd_null()
    
    # 2. ShowWindow RESTORE (in case minimized)
    SW_RESTORE = 9
    SW_SHOW = 5
    ctypes.windll.user32.ShowWindow(hwnd, SW_RESTORE)
    time.sleep(0.3)
    
    # 3. Another null keystroke
    keybd_null()
    
    # 4. SwitchToThisWindow (deprecated but works with keybd_event trick)
    SWITCHTOTHISWINDOW = True  # 1 = bring to front
    ctypes.windll.user32.SwitchToThisWindow(hwnd, ctypes.c_bool(SWITCHTOTHISWINDOW))
    time.sleep(0.5)
    
    print("[FG] Foreground activation complete")


def click_dial_input(window):
    """
    Find and click the number input field in Phone Link's dialer.
    The dialer input is typically above the dial pad in the Calls view.
    """
    rect = window.BoundingRectangle
    w = rect.right - rect.left  # width
    h = rect.bottom - rect.top  # height
    # Number input field is center-right area, above the dial pad
    # Based on visual inspection: roughly 65% across, 18% down
    cx = int(rect.left + w * 0.65)
    cy = int(rect.top + h * 0.18)
    
    print(f"[CLICK] Dial input at ({cx}, {cy}) — window rect: L={rect.left} T={rect.top} W={w} H={h}")
    pyautogui.click(cx, cy)
    time.sleep(0.5)


def type_number(phone: str):
    """Type phone number using clipboard paste (most reliable)."""
    import pyperclip
    pyperclip.copy(phone)
    time.sleep(0.1)
    pyautogui.hotkey("ctrl", "a")  # select all existing text
    time.sleep(0.15)
    pyautogui.hotkey("ctrl", "v")  # paste
    time.sleep(0.3)
    print(f"[TYPE] Pasted phone: {phone}")


def press_enter_call():
    """Press Enter to initiate the call."""
    pyautogui.press("enter")
    time.sleep(0.5)
    print("[CALL] Enter pressed — call initiated")


# ════════════════════════════════════════════════════════════
# MAIN SEQUENCE
# ════════════════════════════════════════════════════════════

def main():
    global step
    print("=" * 60)
    print(f"Phone Link Stepped Dialer — phone: {PHONE}")
    print("=" * 60)
    
    # STEP 1: Baseline screenshot
    print("\n--- Step 1: Baseline ---")
    screenshot("baseline")
    
    # STEP 2: Null keystroke (foreground unlock)
    print("\n--- Step 2: keybd_event null ---")
    keybd_null()
    screenshot("after_keybd_null")
    
    # STEP 3: Find Phone Link
    print("\n--- Step 3: Find Phone Link window ---")
    pl = find_phone_link_window()
    if not pl:
        print("[FAIL] Phone Link not found!")
        screenshot("fail_no_phonelink")
        return False
    screenshot("found_phonelink")
    
    # STEP 4: Bring to foreground
    print("\n--- Step 4: Bring to foreground ---")
    bring_to_foreground(pl)
    screenshot("after_fg")
    
    # STEP 5: Switch to Calls panel
    print("\n--- Step 5: Ctrl+3 for Calls ---")
    pyautogui.hotkey("ctrl", "3")
    time.sleep(1.5)
    screenshot("after_calls_tab")
    
    # STEP 6: Click dial input
    print("\n--- Step 6: Click dial input ---")
    click_dial_input(pl)
    screenshot("after_click_dial")
    
    # STEP 7: Type number
    print("\n--- Step 7: Type phone number ---")
    type_number(PHONE)
    screenshot("after_type_number")
    
    # STEP 8: Press Enter to call
    print("\n--- Step 8: Press Enter to call ---")
    press_enter_call()
    screenshot("after_enter_call")
    
    print("\n" + "=" * 60)
    print(f"DONE — {step} screenshots saved to {SCREENSHOT_DIR}")
    print("=" * 60)
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
