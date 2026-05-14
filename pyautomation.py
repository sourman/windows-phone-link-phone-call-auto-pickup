"""
Python (PyAutoGUI + pywin32) replacement for the AHK automation scripts.

Replicates:
  - open-comet-voice.ahk  →  open_comet_voice()
  - enter_number_2.ahk    →  enter_number()

Usage:
  python pyautomation.py comet [target_url]
  python pyautomation.py call <phone_number>
  python pyautomation.py both [target_url] [phone_number]

Dependencies:
  pip install pyautogui Pillow psutil pywin32 opencv-python
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import psutil
import pyautogui
import pygetwindow as gw

try:
    import win32con
    import win32gui
    import win32process

    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent
LOG_FILE = REPO_ROOT / "pyautomation.log"
ASSETS_DIR = REPO_ROOT / "assets"
CALL_BUTTON_IMAGE = ASSETS_DIR / "call_button-green-tight.png"
TARGET_URL_FILE = REPO_ROOT / "target_url.txt"
SCREENSHOT_DIR = REPO_ROOT / "screenshots"

COMET_EXE_NAME = "comet.exe"
COMET_PATH = Path(os.environ.get("LOCALAPPDATA", "")) / "Perplexity" / "Comet" / "Application" / "comet.exe"
PHONE_LINK_TITLE = "Phone Link"
PHONE_LINK_URI = "ms-phone://"

HARDCODED_PHONE = "01280043725"

pyautogui.PAUSE = 0.05  # small pause between actions

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

log = logging.getLogger("pyautomation")


def _setup_logging() -> None:
    handler = logging.FileHandler(str(LOG_FILE), encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logging.root.addHandler(handler)
    logging.root.setLevel(logging.INFO)


def _screenshot_path(label: str) -> Path:
    """Return a timestamped screenshot path, creating the directory if needed."""
    SCREENSHOT_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return SCREENSHOT_DIR / f"{ts}_{label}.png"


def _save_screenshot(label: str, region: tuple[int, int, int, int] | None = None) -> Path:
    """Take and save a screenshot (full screen or cropped region)."""
    path = _screenshot_path(label)
    img = pyautogui.screenshot(region=region) if region else pyautogui.screenshot()
    img.save(str(path))
    log.info("Screenshot saved: %s", path.name)
    return path


# ---------------------------------------------------------------------------
# Window helpers (Windows-specific via pywin32)
# ---------------------------------------------------------------------------


def _find_windows_by_pid(pid: int) -> list[int]:
    """Return top-level window handles owned by *pid*."""
    if not HAS_WIN32:
        return []
    result: list[int] = []

    def _cb(hwnd: int, _ctx: None) -> None:
        _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
        if found_pid == pid and win32gui.IsWindowVisible(hwnd):
            result.append(hwnd)

    win32gui.EnumWindows(_cb, None)
    return result


def _find_windows_by_exe(exe_name: str) -> list[tuple[int, int]]:
    """Return [(hwnd, pid), ...] for all visible windows whose process matches *exe_name*."""
    targets: list[tuple[int, int]] = []
    exe_lower = exe_name.lower()
    for proc in psutil.process_iter(["pid", "name"]):
        if (proc.info.get("name") or "").lower() == exe_lower:
            for hwnd in _find_windows_by_pid(proc.info["pid"]):
                targets.append((hwnd, proc.info["pid"]))
    return targets


def _close_window(hwnd: int, timeout: float = 5.0) -> bool:
    """Send WM_CLOSE and wait for the window to disappear."""
    if not HAS_WIN32:
        return False
    win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not win32gui.IsWindow(hwnd):
            return True
        time.sleep(0.1)
    return False


def _activate_window(hwnd: int, timeout: float = 10.0) -> bool:
    """Bring window to foreground and wait until it's active."""
    if not HAS_WIN32:
        return False
    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    win32gui.SetForegroundWindow(hwnd)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if win32gui.GetForegroundWindow() == hwnd:
            return True
        time.sleep(0.1)
    return False


def _wait_for_window(title: str, timeout: float = 10.0) -> gw.Win32Window | None:
    """Wait until a window with *title* appears."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        wins = gw.getWindowsWithTitle(title)
        if wins:
            return wins[0]
        time.sleep(0.2)
    return None


def _wait_for_window_count(exe_name: str, count: int, timeout: float = 10.0) -> list[tuple[int, int]]:
    """Wait until at least *count* windows exist for *exe_name*."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        wins = _find_windows_by_exe(exe_name)
        if len(wins) >= count:
            return wins
        time.sleep(0.1)
    return _find_windows_by_exe(exe_name)


# ---------------------------------------------------------------------------
# Comet voice (replaces open-comet-voice.ahk)
# ---------------------------------------------------------------------------


def open_comet_voice(target_url: str | None = None) -> bool:
    """
    Open Comet browser with a fresh session and optionally navigate to target_url,
    then activate voice mode with Alt+Shift+V.

    Returns True on success.
    """
    log.info("open_comet_voice starting — target_url=%s", target_url or "(none)")

    if not HAS_WIN32:
        log.error("pywin32 is required for window management")
        return False

    # --- Close existing Comet windows ---
    existing = _find_windows_by_exe(COMET_EXE_NAME)
    log.info("Found %d existing Comet window(s)", len(existing))
    for hwnd, _pid in existing:
        _close_window(hwnd)
    if existing:
        time.sleep(1.0)

    # --- First Comet window ---
    if not COMET_PATH.is_file():
        log.error("Comet not found at %s", COMET_PATH)
        return False

    log.info("Launching first Comet window...")
    subprocess.Popen([str(COMET_PATH)], cwd=str(COMET_PATH.parent))

    first_windows = _wait_for_window_count(COMET_EXE_NAME, 1, timeout=10)
    if not first_windows:
        log.error("First Comet window did not appear")
        return False

    first_hwnd, _ = first_windows[0]
    log.info("First Comet window: hwnd=%s", first_hwnd)

    time.sleep(5)  # match AHK's 5s delay

    # --- Second Comet window (fresh-session trick) ---
    log.info("Launching second Comet window...")
    subprocess.Popen([str(COMET_PATH)], cwd=str(COMET_PATH.parent))

    second_windows = _wait_for_window_count(COMET_EXE_NAME, 2, timeout=10)
    if len(second_windows) < 2:
        log.error("Could not find two Comet windows (found %d)", len(second_windows))
        return False

    # Identify the new window (not first_hwnd)
    second_hwnd = None
    for hwnd, pid in second_windows:
        if hwnd != first_hwnd:
            second_hwnd = hwnd
            break

    if second_hwnd is None:
        log.error("Could not identify second Comet window")
        return False

    log.info("Second Comet window: hwnd=%s", second_hwnd)

    # Close the first window
    _close_window(first_hwnd)
    log.info("Closed first window (hwnd=%s)", first_hwnd)
    time.sleep(0.5)

    # Activate the second window
    if not _activate_window(second_hwnd):
        log.error("Second Comet window did not become active")
        return False
    log.info("Activated second window (hwnd=%s)", second_hwnd)

    # --- Navigate to target URL ---
    if target_url:
        time.sleep(0.5)
        log.info("Navigating to target URL: %s", target_url)

        # Ctrl+L with explicit key events — pyautogui.hotkey is too fast for Electron
        pyautogui.keyDown("ctrl")
        time.sleep(0.05)
        pyautogui.press("l")
        time.sleep(0.05)
        pyautogui.keyUp("ctrl")
        time.sleep(0.5)

        pyautogui.write(target_url, interval=0.03)
        time.sleep(0.5)
        pyautogui.press("enter")
        log.info("URL entered and Enter sent")
        time.sleep(2)

    # --- Activate voice mode ---
    log.info("Activating voice mode (Alt+Shift+V)")
    # Re-activate window in case focus shifted during navigation
    _activate_window(second_hwnd, timeout=3)
    time.sleep(0.3)
    pyautogui.keyDown("alt")
    time.sleep(0.05)
    pyautogui.keyDown("shift")
    time.sleep(0.05)
    pyautogui.press("v")
    time.sleep(0.05)
    pyautogui.keyUp("shift")
    time.sleep(0.05)
    pyautogui.keyUp("alt")
    log.info("Voice mode keystroke sent")
    time.sleep(3)  # wait for voice mode to fully activate before next step steals focus

    log.info("open_comet_voice done")
    return True


# ---------------------------------------------------------------------------
# Phone Link call (replaces enter_number_2.ahk)
# ---------------------------------------------------------------------------


def enter_number(phone: str) -> bool:
    """
    Open Phone Link, switch to Calls panel, enter *phone*, find and click
    the call button (image search), then close Phone Link.

    Returns True on success.
    """
    log.info("enter_number starting — phone=%s", phone)

    if not HAS_WIN32:
        log.error("pywin32 is required for window management")
        return False

    # --- Close Phone Link to refresh state ---
    wins = gw.getWindowsWithTitle(PHONE_LINK_TITLE)
    if wins:
        log.info("Closing Phone Link to freshen state...")
        wins[0].close()
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if not gw.getWindowsWithTitle(PHONE_LINK_TITLE):
                break
            time.sleep(0.2)
        time.sleep(0.5)

    # --- Open Phone Link ---
    log.info("Launching Phone Link via %s", PHONE_LINK_URI)
    os.startfile(PHONE_LINK_URI)

    pl_win = _wait_for_window(PHONE_LINK_TITLE, timeout=15)
    if not pl_win:
        log.error("Phone Link did not launch within 15s")
        return False

    time.sleep(2.0)  # extra load time for full render

    # --- Switch to Calls panel ---
    pl_win.activate()
    time.sleep(0.3)
    pyautogui.hotkey("ctrl", "3")
    time.sleep(0.5)

    # --- Type phone number ---
    pyautogui.typewrite(phone, interval=0.02)
    time.sleep(0.5)

    # --- Scroll down in Phone Link window ---
    try:
        rect = pl_win.box
        center_x = rect.left + rect.width // 2
        center_y = rect.top + rect.height // 2
        pyautogui.moveTo(center_x, center_y)
        for _ in range(5):
            pyautogui.scroll(-1)  # negative = scroll down
        time.sleep(0.3)
    except Exception:
        log.warning("Could not scroll in Phone Link window")

    # --- Image search for call button ---
    if CALL_BUTTON_IMAGE.is_file():
        log.info("Searching for call button image...")
        try:
            pl_win.activate()
            time.sleep(0.2)

            # Screenshot: before click (full screen)
            _save_screenshot("pre_call_button")

            rect = pl_win.box
            screenshot = pyautogui.screenshot(
                region=(rect.left, rect.top, rect.width, rect.height)
            )

            # Search with confidence threshold — green template matches well
            matches = list(
                pyautogui.locateAll(
                    str(CALL_BUTTON_IMAGE),
                    screenshot,
                    confidence=0.8,
                )
            )

            if matches:
                match = matches[0]
                click_x = rect.left + match.left + match.width // 2
                click_y = rect.top + match.top + match.height // 2
                log.info("Found call button at (%d, %d) — clicking", click_x, click_y)

                # Screenshot: 200x200 crop around the matched button
                from PIL import Image
                crop = screenshot.crop((
                    max(0, match.left - 60),
                    max(0, match.top - 60),
                    match.left + match.width + 60,
                    match.top + match.height + 60,
                ))
                crop_path = _screenshot_path("call_button_crop")
                crop.save(str(crop_path))
                log.info("Button crop saved: %s", crop_path.name)

                pyautogui.click(click_x, click_y)
                time.sleep(0.5)

                # Screenshot: after click (full screen)
                _save_screenshot("post_call_button")
                log.info("Clicked call button")
            else:
                log.info("Call button image not found — falling back to Enter")
                pyautogui.press("enter")
        except Exception as e:
            log.warning("Image search failed (%s) — falling back to Enter", e)
            pyautogui.press("enter")
    else:
        log.info("Call button image not found at %s — using Enter", CALL_BUTTON_IMAGE)
        pyautogui.press("enter")

    # --- Close Phone Link ---
    wins = gw.getWindowsWithTitle(PHONE_LINK_TITLE)
    if wins:
        wins[0].close()

    log.info("enter_number done")
    return True


# ---------------------------------------------------------------------------
# Combined runner
# ---------------------------------------------------------------------------


def run_comet_then_call(phone: str = HARDCODED_PHONE, target_url: str | None = None) -> tuple[bool, bool]:
    """Run both steps: open Comet voice, then dial phone."""
    comet_ok = open_comet_voice(target_url)
    call_ok = enter_number(phone)
    return comet_ok, call_ok


def read_target_url() -> str | None:
    if not TARGET_URL_FILE.exists():
        return None
    url = TARGET_URL_FILE.read_text().strip()
    return url or None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    _setup_logging()

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
