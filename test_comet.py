"""
Test harness for Comet + Phone Link automation.
Runs the flow, takes screenshots at each step, reports results.
"""
import logging
import os
import sys
import time
from pathlib import Path

import pyautogui

# Setup
REPO_ROOT = Path(__file__).resolve().parent
SCREEN_DIR = REPO_ROOT / "test_screenshots"
SCREEN_DIR.mkdir(exist_ok=True)

# Setup logging to console + file
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(REPO_ROOT / "test_comet.log", encoding="utf-8", mode="w"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("test")

# Import pyautomation
sys.path.insert(0, str(REPO_ROOT))
import pyautomation

pyautomation._setup_logging()

step = 0

def screenshot(label: str) -> Path:
    global step
    step += 1
    path = SCREEN_DIR / f"{step:02d}_{label}.png"
    img = pyautogui.screenshot()
    img.save(str(path))
    log.info("📸 Screenshot: %s", path.name)
    return path

def test_comet_flow():
    """Test the full Comet + Phone Link flow with visual verification."""
    target_url = "http://localhost:18789/chat?session=agent%3Amain%3Atelegram%3Agroup%3A-1003918620814"
    phone = "01280043725"

    log.info("=" * 60)
    log.info("TEST: Comet + Phone Link flow")
    log.info("=" * 60)

    # Step 1: Close existing Comet
    log.info("Step 1: Closing existing Comet windows...")
    existing = pyautomation._find_windows_by_exe(pyautomation.COMET_EXE_NAME)
    for hwnd, _pid in existing:
        pyautomation._close_window(hwnd)
    if existing:
        time.sleep(1.0)
    screenshot("pre_start")

    # Step 2: Launch first Comet
    log.info("Step 2: Launching first Comet window...")
    import subprocess
    subprocess.Popen([str(pyautomation.COMET_PATH)], cwd=str(pyautomation.COMET_PATH.parent))
    first_windows = pyautomation._wait_for_window_count(pyautomation.COMET_EXE_NAME, 1, timeout=15)
    if not first_windows:
        log.error("FAILED: First Comet window did not appear")
        return False
    first_hwnd = first_windows[0][0]
    log.info("First Comet: hwnd=%s", first_hwnd)
    time.sleep(5)
    screenshot("first_comet")

    # Step 3: Launch second Comet
    log.info("Step 3: Launching second Comet window...")
    subprocess.Popen([str(pyautomation.COMET_PATH)], cwd=str(pyautomation.COMET_PATH.parent))
    second_windows = pyautomation._wait_for_window_count(pyautomation.COMET_EXE_NAME, 2, timeout=15)
    if len(second_windows) < 2:
        log.error("FAILED: Only %d Comet windows found", len(second_windows))
        return False
    second_hwnd = None
    for hwnd, pid in second_windows:
        if hwnd != first_hwnd:
            second_hwnd = hwnd
            break
    log.info("Second Comet: hwnd=%s", second_hwnd)
    screenshot("two_comets")

    # Step 4: Close first, activate second
    log.info("Step 4: Closing first, activating second...")
    pyautomation._close_window(first_hwnd)
    time.sleep(0.5)
    activated = pyautomation._activate_window(second_hwnd)
    log.info("Activation result: %s", activated)
    time.sleep(0.5)
    screenshot("after_activate")

    # Step 5: Verify Comet is foreground
    import win32gui
    fg = win32gui.GetForegroundWindow()
    fg_title = win32gui.GetWindowText(fg)
    log.info("Foreground window: hwnd=%s title='%s'", fg, fg_title)
    is_comet_fg = (fg == second_hwnd)
    log.info("Comet is foreground: %s", is_comet_fg)
    if not is_comet_fg:
        log.warning("Comet NOT foreground — keystrokes will go to '%s'", fg_title)

    # Step 6: Ctrl+L to focus URL bar
    log.info("Step 6: Ctrl+L to focus URL bar...")
    pyautogui.keyDown("ctrl")
    time.sleep(0.05)
    pyautogui.press("l")
    time.sleep(0.05)
    pyautogui.keyUp("ctrl")
    time.sleep(0.8)
    screenshot("after_ctrl_l")

    # Step 7: Type URL
    log.info("Step 7: Typing URL...")
    pyautogui.write(target_url, interval=0.03)
    time.sleep(0.5)
    screenshot("url_typed")

    # Step 8: Press Enter
    log.info("Step 8: Pressing Enter...")
    pyautogui.press("enter")
    time.sleep(2)
    screenshot("after_navigate")

    # Step 9: Voice mode
    log.info("Step 9: Activating voice mode (Alt+Shift+V)...")
    pyautomation._activate_window(second_hwnd, timeout=3)
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
    time.sleep(2)
    screenshot("voice_mode")

    # Step 10: Phone Link call
    log.info("Step 10: Initiating Phone Link call via UIA...")
    call_ok = pyautomation.enter_number(phone)
    log.info("Phone Link call result: %s", call_ok)
    time.sleep(1)
    screenshot("phone_link")

    log.info("=" * 60)
    log.info("DONE: comet_foreground=%s call_ok=%s", is_comet_fg, call_ok)
    log.info("Screenshots saved to: %s", SCREEN_DIR)
    log.info("=" * 60)
    return is_comet_fg and call_ok

if __name__ == "__main__":
    test_comet_flow()
