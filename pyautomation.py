"""
Auto-pickup — UIA-based Comet voice activation + AHK Phone Link calling.

Comet launching: UIA window discovery + keyboard shortcuts
Phone Link calling: delegates to phone_call.ahk (proven reliable, same as telegram-call)

Usage:
  python pyautomation.py comet [target_url]
  python pyautomation.py call <phone_number>
  python pyautomation.py both [target_url] [phone_number]

Dependencies:
  pip install uiautomation pyautogui pyperclip psutil
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

SCRIPT_DIR = Path(__file__).resolve().parent
LOG_FILE = SCRIPT_DIR / "pyautomation.log"
TARGET_URL_FILE = SCRIPT_DIR / "target_url.txt"

# ── Config ──────────────────────────────────────────────────
COMET_EXE = Path(os.environ.get("LOCALAPPDATA", "")) / "Perplexity" / "Comet" / "Application" / "comet.exe"
HARDCODED_PHONE = "01280043725"

# Phone Link calling via AHK (same proven script from telegram-call repo)
AUTOHOTKEY_EXE = Path(os.environ.get("ProgramFiles", "")) / "AutoHotkey" / "v2" / "AutoHotkey64.exe"
PHONE_CALL_AHK = SCRIPT_DIR / "phone_call.ahk"

# ── Logging ─────────────────────────────────────────────────
logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.info

# ── Imports ─────────────────────────────────────────────────
import uiautomation as auto
import pyautogui
import pyperclip
import psutil

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.03


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
    deadline = time.time() + timeout
    while time.time() < deadline:
        for c in auto.GetRootControl().GetChildren():
            if c.ClassName == "Chrome_WidgetWin_1" and "comet" in (c.Name or "").lower():
                log(f"Found Comet: {c.Name}")
                return c
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
    for c in auto.GetRootControl().GetChildren():
        if c.ClassName == "Chrome_WidgetWin_1" and "comet" in (c.Name or "").lower():
            comet_windows.append(c)

    if len(comet_windows) < 1:
        log("No Comet windows found")
        return False

    if len(comet_windows) >= 2:
        # Close the first one
        first = comet_windows[0]
        first_rect = first.BoundingRectangle
        pyautogui.click(first_rect.right - 15, first_rect.top + 10)
        time.sleep(1)
        log("Closed first Comet window")

    # 5. Find remaining Comet window and bring to foreground
    comet = find_comet_window(timeout=5)
    if not comet:
        log("Comet window lost after closing first")
        return False

    # Activate by clicking title bar
    rect = comet.BoundingRectangle
    pyautogui.click(rect.left + 100, rect.top + 10)
    time.sleep(1)

    # 6. Navigate to URL if provided
    if target_url:
        log(f"Navigating to: {target_url}")
        pyautogui.hotkey("ctrl", "l")
        time.sleep(0.5)
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


# ── Phone Link call (AHK) ───────────────────────────────────

def enter_number(phone: str) -> bool:
    """
    Dial phone number via Phone Link using the proven AHK script.

    This is the same phone_call.ahk used by telegram-call repo.
    """
    log(f"=== enter_number (AHK) — phone={phone} ===")

    if not AUTOHOTKEY_EXE.is_file():
        log(f"AHK not found: {AUTOHOTKEY_EXE}")
        return False

    if not PHONE_CALL_AHK.is_file():
        log(f"AHK script not found: {PHONE_CALL_AHK}")
        return False

    try:
        result = subprocess.run(
            [str(AUTOHOTKEY_EXE), str(PHONE_CALL_AHK), phone],
            capture_output=True, timeout=60,
        )
        log(f"AHK exited with code {result.returncode}")
    except subprocess.TimeoutExpired:
        log("AHK script timed out after 60s")
        return False
    except Exception as e:
        log(f"AHK execution error: {e}")
        return False

    log("=== enter_number done ===")
    return result.returncode == 0


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
