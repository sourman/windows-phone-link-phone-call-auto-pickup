"""
Phone Link dialer v6 — FINAL VERSION.
- Minimize competing windows (Comet) first
- keybd_null for foreground unlock  
- Bring PL to foreground PROPERLY
- Clear old digits from accumulator
- Type number into edit field
- Use UIA .Click() on Call button (works even when virtual/off-screen!)
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


def keybd_null():
    """Null keystroke to satisfy Windows foreground lock condition."""
    u = ctypes.windll.user32
    u.keybd_event(0, 0, 0, 0)
    u.keybd_event(0, 0, 0x0002, 0)  # KEYUP
    time.sleep(0.3)


def set_foreground_win32(hwnd):
    """
    Aggressive foreground activation:
    1. keybd_null (we are "last input")
    2. ShowWindow RESTORE
    3. keybd_null again
    4. SetForegroundWindow
    5. Optional: SwitchToThisWindow
    """
    SW_RESTORE = 9
    SW_SHOW = 5
    
    keybd_null()
    
    # Restore if minimized
    ctypes.windll.user32.ShowWindow(hwnd, SW_RESTORE)
    time.sleep(0.2)
    
    # Bring to front
    keybd_null()
    result = ctypes.windll.user32.SetForegroundWindow(hwnd)
    print(f"[FG] SetForegroundWindow result={result}")
    time.sleep(0.2)
    
    if not result:
        # Fallback: SwitchToThisWindow
        keybd_null()
        ctypes.windll.user32.SwitchToThisWindow(hwnd, True)
        print("[FG] Used SwitchToThisWindow fallback")
    
    time.sleep(0.5)


def find_pl():
    for c in auto.GetRootControl().GetChildren():
        if "phone link" in (c.Name or "").lower():
            return c
    return None


def find_by_aid(root, aid, max_depth=6):
    """BFS find by AutomationId."""
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


def minimize_comet():
    """Minimize Comet windows so they don't steal focus."""
    import psutil
    for proc in psutil.process_iter(["pid", "name"]):
        name = (proc.info.get("name") or "").lower()
        if "comet" in name:
            try:
                import subprocess
                # Use PowerShell to minimize comet windows
                subprocess.run([
                    "powershell.exe", "-Command",
                    f'Get-Process -Name comet -ErrorAction SilentlyContinue | '
                    'Where-Object { $_.MainWindowHandle -ne 0 } | '
                    'ForEach-Object { '
                    '  Add-Type @"using System;using System.Runtime.InteropServices;'
                    'public class M{{[DllImport(""user32.dll"")]'
                    'public static extern bool ShowWindow(IntPtr h,int c);}}";'
                    '  [M]::ShowWindow($_.MainWindowHandle,6)'  # SW_MINIMIZE=6
                    '}'
                ], capture_output=True, timeout=5)
                print(f"[COMET] Minimized PID {proc.info['pid']}")
            except Exception as e:
                print(f"[COMET] Error minimizing: {e}")
            break


def clear_accumulator(pl):
    """
    Clear any existing digits from the dialer.
    Strategy: click EditControl, Ctrl+A, Delete/Backspace x20
    """
    edit = find_by_aid(pl, 'TextBox')
    if edit:
        rect = edit.BoundingRectangle
        if rect.left != 0 or rect.right != 0:
            cx = int((rect.left + rect.right) / 2)
            cy = int((rect.top + rect.bottom) / 2)
            pyautogui.click(cx, cy)
            time.sleep(0.3)
    
    # Select all + delete
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.15)
    # Send multiple backspaces to be thorough
    for _ in range(20):
        pyautogui.press("backspace")
        time.sleep(0.02)
    time.sleep(0.3)
    print("[CLEAR] Accumulator cleared")


def type_number(edit_ctrl, phone):
    """Click edit control, then type each digit as keystroke."""
    rect = edit_ctrl.BoundingRectangle
    cx = int((rect.left + rect.right) / 2)
    cy = int((rect.top + rect.bottom) / 2)
    
    print(f"[TYPE] Clicking edit at ({cx},{cy})")
    pyautogui.click(cx, cy)
    time.sleep(0.5)
    
    # Select all first (in case of leftover text)
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.1)
    
    # Type digit by digit
    print(f"[TYPE] Typing: {phone}")
    for i, digit in enumerate(phone):
        pyautogui.press(digit)
        time.sleep(0.06)
    time.sleep(0.5)
    print(f"[TYPE] Done")


def uia_click_call(pl):
    """
    Find ButtonCall and use UIA .Click() method.
    This works even when button is virtualized/off-screen!
    """
    btn = find_by_aid(pl, 'ButtonCall')
    if not btn:
        print("[CALL] ButtonCall NOT found!")
        return False
    
    r = btn.BoundingRectangle
    print(f"[CALL] Found '{btn.Name}' rect=[{r.left},{r.top},{r.right},{r.bottom}]")
    
    # Use UIA's native Click() — works on virtual controls!
    try:
        btn.Click()
        print("[CALL] UIA .Click() called successfully")
        return True
    except Exception as e:
        print(f"[CALL] .Click() failed: {e}, trying InvokePattern...")
        try:
            ip = btn.GetInvokePattern()
            ip.Invoke()
            print("[CALL] InvokePattern.Invoke() succeeded")
            return True
        except Exception as e2:
            print(f"[CALL] Invoke also failed: {e2}")
            return False


# ════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════

def main():
    global step
    print("=" * 60)
    print(f"Phone Link Dialer v6 (FINAL) — phone: {PHONE}")
    print("=" * 60)

    # STEP 1: Baseline
    screenshot("01_baseline")

    # STEP 2: Minimize Comet (stop it stealing focus)
    print("\n[PREP] Minimizing Comet...")
    minimize_comet()
    time.sleep(0.5)
    screenshot("02_comet_minimized")

    # STEP 3: Null keystroke
    keybd_null()
    screenshot("03_keybd")

    # STEP 4: Find PL
    pl = find_pl()
    if not pl:
        print("[FAIL] No Phone Link!")
        screenshot("FAIL_nopl")
        return False
    hwnd = pl.NativeWindowHandle
    print(f"[FIND] Phone Link HWND={hwnd}")
    screenshot("04_found_pl")

    # STEP 5: Aggressive foreground
    print("\n[FG] Bringing PL to foreground...")
    set_foreground_win32(hwnd)
    screenshot("05_fg")

    # STEP 6: Verify FG worked
    fg_hwnd = ctypes.windll.user32.GetForegroundWindow()
    print(f"[FG CHECK] Current foreground HWND={fg_hwnd} (PL={hwnd}, match={fg_hwnd==hwnd})")
    if fg_hwnd != hwnd:
        print("[FG CHECK] WARNING: PL is NOT in foreground! Retrying...")
        time.sleep(0.5)
        set_foreground_win32(hwnd)
        fg_hwnd2 = ctypes.windll.user32.GetForegroundWindow()
        print(f"[FG CHECK] Retry: current FG HWND={fg_hwnd2} (match={fg_hwnd2==hwnd})")
        screenshot("05b_fg_retry")

    # STEP 7: Ctrl+3 → Calls tab
    print("\n[TAB] Ctrl+3 → Calls tab")
    pyautogui.hotkey("ctrl", "3")
    time.sleep(1.5)
    screenshot("06_calls_tab")

    # STEP 8: Clear accumulator
    print("\n[CLEAR] Clearing old digits...")
    clear_accumulator(pl)
    screenshot("07_cleared")

    # STEP 9: Find edit control + type number
    edit = find_by_aid(pl, 'TextBox')
    if not edit:
        print("[FAIL] TextBox not found!")
        screenshot("FAIL_noedit")
        return False
    
    type_number(edit, PHONE)
    screenshot("08_typed")

    # STEP 10: UIA Click on Call button
    print("\n[CALL] Using UIA .Click() on Call button...")
    call_ok = uia_click_call(pl)
    screenshot("09_call_clicked")

    # Wait for call to connect
    time.sleep(3)
    screenshot("10_final")

    # Final FG check
    final_fg = ctypes.windll.user32.GetForegroundWindow()
    print(f"\n[FINAL] Foreground HWND={final_fg}")

    print(f"\n{'=' * 60}")
    print(f"DONE — {step} screenshots saved")
    print(f"Call launched: {call_ok}")
    print(f"{'=' * 60}")
    return call_ok


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
