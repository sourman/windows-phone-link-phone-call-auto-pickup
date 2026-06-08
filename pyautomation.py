"""
Auto-pickup — UIA-based Comet voice activation + Phone Link calling.

Comet launching: UIA window discovery + keyboard shortcuts
Phone Link calling: UIA tree navigation + keypad coordinate clicks + Enter

Usage:
  python pyautomation.py comet [target_url]
  python pyautomation.py call <phone_number>
  python pyautomation.py endcall
  python pyautomation.py both [target_url] [phone_number]

Dependencies:
  pip install uiautomation pyautogui psutil
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
from pathlib import Path

sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', errors='replace', closefd=False)
sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', errors='replace', closefd=False)

import ctypes

# DPI awareness for correct coordinate calculations on high-DPI displays
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
except (AttributeError, OSError):
    pass  # shcore not available on older Windows

u32 = ctypes.windll.user32

SCRIPT_DIR = Path(__file__).resolve().parent
LOG_FILE = SCRIPT_DIR / "pyautomation.log"
TARGET_URL_FILE = SCRIPT_DIR / "target_url.txt"

# ── Config ──────────────────────────────────────────────────
COMET_EXE = Path(os.environ.get("LOCALAPPDATA", "")) / "Perplexity" / "Comet" / "Application" / "comet.exe"
HARDCODED_PHONE = "01280043725"

# ── Logging ─────────────────────────────────────────────────
logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.info

# ── Imports ─────────────────────────────────────────────────
import pyautogui
import psutil

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.03


def _force_foreground(hwnd: int) -> bool:
    """Bring window to foreground using ALT key bypass for SetForegroundWindow."""
    u32.keybd_event(0x12, 0, 0, 0)       # ALT down
    u32.keybd_event(0x12, 0, 0x0002, 0)  # ALT up
    u32.ShowWindow(hwnd, 9)               # SW_RESTORE
    return bool(u32.SetForegroundWindow(hwnd))


def _ensure_uia():
    """Lazy import UIA — only when actually needed for automation."""
    import uiautomation as auto
    return auto


_SKIP_SUBTREES = frozenset([
    "NotificationsList", "NotificationsListScrollHost",
    "PaneContent", "MainContentGrid", "PinnedNotificationsList",
])


def _find_by_autoid(ctrl, target_aid: str, depth: int = 0):
    """Recursively find a control by AutomationId, skipping notification subtrees."""
    if depth > 20:
        return None
    try:
        for child in ctrl.GetChildren():
            aid = child.AutomationId or ""
            if aid == target_aid:
                return child
            if aid in _SKIP_SUBTREES:
                continue
            result = _find_by_autoid(child, target_aid, depth + 1)
            if result:
                return result
    except Exception:
        pass
    return None


# ── Comet helpers ───────────────────────────────────────────

def kill_comet():
    """Kill all Comet processes."""
    for proc in psutil.process_iter(["pid", "name"]):
        if (proc.info.get("name") or "").lower() == "comet.exe":
            log(f"Killing Comet PID {proc.info['pid']}")
            proc.kill()
    time.sleep(1)


def launch_comet():
    """Launch Comet browser."""
    if not COMET_EXE.is_file():
        log(f"Comet not found at {COMET_EXE}")
        return False
    subprocess.Popen([str(COMET_EXE)], cwd=str(COMET_EXE.parent))
    log("Comet launched")
    return True


def find_comet_window(timeout=10):
    """Find Comet window by class name."""
    auto = _ensure_uia()
    deadline = time.time() + timeout
    while time.time() < deadline:
        for c in auto.GetRootControl().GetChildren():
            try:
                if c.ClassName == "Chrome_WidgetWin_1" and "comet" in (c.Name or "").lower():
                    log(f"Found Comet: {c.Name}")
                    return c
            except Exception:
                pass
        time.sleep(0.5)
    log("Comet window not found")
    return None


# ── Comet voice activation ──────────────────────────────────

def open_comet_voice(target_url: str | None = None) -> bool:
    """
    Open Comet with fresh session, navigate to URL, activate voice mode.

    Uses the two-window trick for session isolation.
    Keyboard shortcuts for URL bar (Ctrl+L) and voice (Alt+Shift+V).
    """
    log("=== open_comet_voice starting ===")

    # 1. Kill existing Comet
    kill_comet()

    # 2. Launch first Comet window
    if not launch_comet():
        return False
    time.sleep(5)

    # 3. Launch second window (fresh session trick)
    if not launch_comet():
        return False
    time.sleep(3)

    # 4. Find and close the first Comet window, keep the second
    comet_windows = []
    for c in _get_root_children():
        try:
            if c.ClassName == "Chrome_WidgetWin_1" and "comet" in (c.Name or "").lower():
                comet_windows.append(c)
        except Exception:
            pass  # skip stale elements

    if len(comet_windows) < 1:
        log("No Comet windows found")
        return False

    if len(comet_windows) >= 2:
        # Close the LAST (oldest/background) one.
        # Root children are in Z-order (topmost first), so
        # comet_windows[0] is the foreground window — that's the
        # fresh second launch we want to keep.
        old = comet_windows[-1]
        old_rect = old.BoundingRectangle
        pyautogui.click(old_rect.right - 15, old_rect.top + 10)
        time.sleep(1)
        log("Closed old Comet window (kept foreground)")

    # 5. Find remaining Comet window and bring to foreground
    comet = find_comet_window(timeout=5)
    if not comet:
        log("Comet window lost after closing first")
        return False

    # Activate by clicking title bar
    rect = comet.BoundingRectangle
    _force_foreground(comet.NativeWindowHandle)
    time.sleep(0.5)
    pyautogui.click(rect.left + 100, rect.top + 10)
    time.sleep(0.5)

    # 6. Navigate to URL if provided
    if target_url:
        log(f"Navigating to: {target_url}")
        pyautogui.hotkey("ctrl", "l")
        time.sleep(0.5)
        import pyperclip
        pyperclip.copy(target_url)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.3)
        pyautogui.press("enter")
        time.sleep(3)
        log("URL navigated")

    # 7. Activate voice mode (Alt+Shift+V)
    log("Activating voice mode (Alt+Shift+V)")
    pyautogui.click(rect.left + 200, rect.top + 200)
    time.sleep(0.3)
    pyautogui.hotkey("alt", "shift", "v")
    time.sleep(2)
    log("Voice mode keystroke sent")

    log("=== open_comet_voice done ===")
    return True


# ── Phone Link call (UIA) ───────────────────────────────────

def _get_root_children():
    """Get root UIA children with retry — tree walker can crash transiently."""
    auto = _ensure_uia()
    for attempt in range(3):
        try:
            return list(auto.GetRootControl().GetChildren())
        except Exception:
            log(f"UIA tree walk failed (attempt {attempt+1}/3), retrying...")
            time.sleep(0.5 * (attempt + 1))
    return []


def _find_phone_link():
    """Find main Phone Link window via UIA."""
    best = None
    best_w = 0
    for c in _get_root_children():
        try:
            if c.ClassName == "WinUIDesktopWin32WindowClass" and "phone link" in (c.Name or "").lower():
                rect = c.BoundingRectangle
                w = rect.right - rect.left
                if w > best_w:
                    best = c
                    best_w = w
        except Exception:
            pass
    return best


def _get_phone_link_aumid() -> str | None:
    """Resolve Phone Link's AUMID dynamically via Get-AppxPackage."""
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-AppxPackage *YourPhone* | Select -ExpandProperty PackageFamilyName"],
            capture_output=True, text=True, timeout=10,
        )
        name = result.stdout.strip()
        if name:
            return f"shell:AppsFolder\\{name}!App"
    except Exception:
        pass
    return None


def _ensure_phone_link():
    """Find Phone Link window, launching it if not running."""
    pl = _find_phone_link()
    if pl:
        log("Phone Link already running")
        return pl

    # Try dynamic AUMID first, fall back to hardcoded
    aumid = _get_phone_link_aumid() or "shell:AppsFolder\\Microsoft.YourPhone_8wekyb3d8bbwe!App"
    log(f"Launching Phone Link via {aumid}")
    subprocess.Popen(["explorer.exe", aumid])

    for attempt in range(15):
        time.sleep(1)
        pl = _find_phone_link()
        if pl:
            log(f"Phone Link launched (attempt {attempt + 1})")
            return pl

    log("Phone Link failed to launch")
    return None


def _find_call_window():
    """Find the active Phone Link call window (smaller popup)."""
    for c in _get_root_children():
        try:
            if c.ClassName == "WinUIDesktopWin32WindowClass" and "phone link" in (c.Name or "").lower():
                rect = c.BoundingRectangle
                w = rect.right - rect.left
                if w < 800:
                    return c
        except Exception:
            pass
    return None


def enter_number(phone: str) -> bool:
    """
    Dial phone number via Phone Link using UIA SetValue + click.

    Maximizes Phone Link, switches to dialer (Ctrl+3), sets the number
    via UIA SetValue on the search field, presses Enter to transfer to
    dialer, then clicks the Call button. Verifies the call is on PC.
    """
    log(f"=== enter_number (UIA) — phone={phone} ===")

    pl = _ensure_phone_link()
    if not pl:
        log("Phone Link not available")
        return False

    # Force foreground first, then maximize (order matters — _force_foreground restores window)
    hwnd = pl.NativeWindowHandle
    _force_foreground(hwnd)
    time.sleep(0.3)
    u32.ShowWindow(hwnd, 3)   # SW_MAXIMIZE
    time.sleep(0.5)

    # Click inside window to ensure keyboard focus, then Ctrl+3
    rect = pl.BoundingRectangle
    pyautogui.click(rect.left + 400, rect.top + 200)
    time.sleep(0.3)
    pyautogui.hotkey("ctrl", "3")
    time.sleep(1)

    # Sanity check: verify keypad is visible
    pl = _find_phone_link()
    if not pl:
        log("Phone Link lost after maximize")
        return False
    keypad = _find_by_autoid(pl, "Keypad")
    if not keypad:
        log("Keypad not found — dialer not active")
        return False
    log("Dialer confirmed active")

    # Set phone number in the contact search field via UIA (instant)
    search_box = _find_by_autoid(pl, "ContactSuggestionsBox")
    edit = _find_by_autoid(search_box, "TextBox") if search_box else None
    if not edit:
        log("Search TextBox not found")
        return False
    edit.GetValuePattern().SetValue(phone)
    log(f"Set search field to: {phone}")
    time.sleep(0.3)

    # Enter transfers the number from search to the dialer
    pyautogui.press("enter")
    time.sleep(0.3)

    # Click the Call button (coordinate click, already visible when maximized)
    pl = _find_phone_link()
    keypad = _find_by_autoid(pl, "Keypad")
    if not keypad:
        log("Keypad lost after Enter")
        return False
    for child in keypad.GetChildren():
        if child.AutomationId == "ButtonCall":
            btn_rect = child.BoundingRectangle
            cx = (btn_rect.left + btn_rect.right) // 2
            cy = (btn_rect.top + btn_rect.bottom) // 2
            pyautogui.click(cx, cy)
            log("Call button clicked")
            break
    time.sleep(3)

    # Wait for call window to appear (up to 20s)
    call_win = None
    for attempt in range(20):
        call_win = _find_call_window()
        if call_win:
            break
        time.sleep(1)
    if not call_win:
        log("Call window not found after 20s — call failed")
        return False

    # Check if call is on PC (not on mobile) by looking for transfer button
    transfer_found = False
    for area in call_win.GetChildren():
        def find_transfer(ctrl, depth=0):
            if depth > 10: return None
            try:
                for ch in ctrl.GetChildren():
                    n = (ch.Name or "").lower()
                    if "transfer to mobile" in n or "send call to mobile" in n:
                        return ch
                    r = find_transfer(ch, depth + 1)
                    if r: return r
            except Exception: pass
            return None
        transfer_btn = find_transfer(area)
        if transfer_btn:
            log(f"Call on PC (transfer button present: {transfer_btn.Name!r})")
            transfer_found = True
            break

    if not transfer_found:
        log("Call window found but audio routing could not be confirmed on PC")
        return False

    log("=== enter_number done — call active on PC ===")
    return True


def end_call() -> bool:
    """End active Phone Link call via UIA."""
    log("=== end_call (UIA) ===")

    call_win = _find_call_window()
    if not call_win:
        log("No active call window found")
        return False

    end_btn = _find_by_autoid(call_win, "EndCallButton")
    if not end_btn:
        log("EndCallButton not found")
        return False

    end_btn.GetInvokePattern().Invoke(waitTime=0)
    log("Call ended")

    log("=== end_call done ===")
    return True


# ── Combined runner ─────────────────────────────────────────

def run_comet_then_call(phone: str = HARDCODED_PHONE, target_url: str | None = None) -> tuple[bool, bool]:
    comet_ok = open_comet_voice(target_url)
    call_ok = enter_number(phone)
    return comet_ok, call_ok


def read_target_url() -> str | None:
    if not TARGET_URL_FILE.exists():
        return None
    url = TARGET_URL_FILE.read_text().strip()
    return url or None


# ── CLI ─────────────────────────────────────────────────────

def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "comet":
        url = sys.argv[2] if len(sys.argv) > 2 else read_target_url()
        ok = open_comet_voice(url)
        sys.exit(0 if ok else 1)

    elif cmd == "call":
        phone = sys.argv[2] if len(sys.argv) > 2 else HARDCODED_PHONE
        ok = enter_number(phone)
        sys.exit(0 if ok else 1)

    elif cmd == "endcall":
        ok = end_call()
        sys.exit(0 if ok else 1)

    elif cmd == "both":
        url = sys.argv[2] if len(sys.argv) > 2 else read_target_url()
        phone = sys.argv[3] if len(sys.argv) > 3 else HARDCODED_PHONE
        comet_ok, call_ok = run_comet_then_call(phone, url)
        sys.exit(0 if (comet_ok and call_ok) else 1)

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
