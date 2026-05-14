"""Diagnostic runner for auto-pickup flow.
Steps through open_comet_voice + enter_number with heavy screenshot capture.
Run via: powershell.exe -Command "python diagnose.py"
"""
import sys, os, time, subprocess
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pyautogui
from PIL import Image

SCRIPT_DIR = Path(__file__).resolve().parent
SCREENSHOT_DIR = SCRIPT_DIR / "screenshots"
SCREENSHOT_DIR.mkdir(exist_ok=True)

pyautogui.PAUSE = 0.05
pyautogui.FAILSAFE = True

_step = 0
_log_lines = []

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    line = f"{ts} {msg}"
    _log_lines.append(line)
    print(line)

def ss(label, region=None):
    """Full screenshot."""
    global _step
    _step += 1
    ts = datetime.now().strftime("%H%M%S")
    path = SCREENSHOT_DIR / f"diag_{ts}_{_step:02d}_{label}.png"
    img = pyautogui.screenshot(region=region)
    img.save(str(path))
    log(f"  [SS] SS[{_step:02d}] {label} -> {path.name}")
    return img, str(path)

def crop_around(x, y, size=200, label="crop"):
    """Take a 200x200 centered on (x,y)."""
    global _step
    _step += 1
    ts = datetime.now().strftime("%H%M%S")
    half = size // 2
    region = (
        max(0, int(x) - half),
        max(0, int(y) - half),
        size,
        size,
    )
    path = SCREENSHOT_DIR / f"diag_{ts}_{_step:02d}_{label}.png"
    img = pyautogui.screenshot(region=region)
    img.save(str(path))
    log(f"  [CROP]  CROP[{_step:02d}] {label} @ ({x},{y}) -> {path.name}")
    return str(path)


# ── Step A: Comet Voice ─────────────────────────────────────
log("=" * 60)
log("STEP A: OPEN COMET VOICE")
log("=" * 60)

from pyautomation import (
    _find_windows_by_exe, _close_window, _activate_window,
    COMET_EXE_NAME, COMET_PATH, read_target_url,
    PHONE_LINK_TITLE, CALL_BUTTON_IMAGE,
    _wait_for_window_count, _wait_for_window,
)

target_url = read_target_url()
log(f"Target URL: {target_url or '(none)'}")

# A1: Kill existing Comet
log("--- A1: Kill existing Comet ---")
existing = _find_windows_by_exe(COMET_EXE_NAME)
log(f"Found {len(existing)} existing Comet window(s)")
ss("a1_before_kill")
for hwnd, pid in existing:
    _close_window(hwnd)
if existing:
    time.sleep(1)
ss("a1_after_kill")

# A2: Launch first Comet window
log("--- A2: Launch first Comet ---")
subprocess.Popen([str(COMET_PATH)], cwd=str(COMET_PATH.parent))
first_windows = _wait_for_window_count(COMET_EXE_NAME, 1, timeout=10)
if not first_windows:
    log("FAIL: First Comet window did not appear!")
    sys.exit(1)
first_hwnd, _ = first_windows[0]
log(f"First Comet hwnd={first_hwnd}")
time.sleep(5)
ss("a2_first_comet_launched")

# A3: Launch second Comet window
log("--- A3: Launch second Comet (fresh session trick) ---")
subprocess.Popen([str(COMET_PATH)], cwd=str(COMET_PATH.parent))
second_windows = _wait_for_window_count(COMET_EXE_NAME, 2, timeout=10)
if len(second_windows) < 2:
    log(f"FAIL: Only found {len(second_windows)} Comet windows, need 2")
    sys.exit(1)
second_hwnd = None
for hwnd, pid in second_windows:
    if hwnd != first_hwnd:
        second_hwnd = hwnd
        break
log(f"Second Comet hwnd={second_hwnd}")

# A4: Close first, activate second
log("--- A4: Close first, activate second ---")
_close_window(first_hwnd)
time.sleep(0.5)
ss("a4_first_closed")
# Use taskbar-style activation instead of SetForegroundWindow (blocked by Windows)
ok = False
try:
    ok = _activate_window(second_hwnd)
except Exception as e:
    log(f"_activate_window error: {e}")
if not ok:
    log("SetForegroundWindow failed, trying Alt+Tab fallback...")
    pyautogui.hotkey("alt", "tab")
    time.sleep(0.5)
ss("a4_second_active")

# A5: Navigate to URL
if target_url:
    log(f"--- A5: Navigate to {target_url} ---")
    pyautogui.keyDown("ctrl"); time.sleep(0.05)
    pyautogui.press("l"); time.sleep(0.05)
    pyautogui.keyUp("ctrl"); time.sleep(0.5)
    pyautogui.write(target_url, interval=0.03); time.sleep(0.5)
    pyautogui.press("enter")
    log("URL entered + Enter pressed")
    time.sleep(2)
    ss("a5_after_navigate")

# A6: Voice mode
log("--- A6: Activate voice mode (Alt+Shift+V) ---")
_activate_window(second_hwnd, timeout=3)
# Ensure focus via click if SetForegroundWindow didn't work
pyautogui.click(500, 400)  # center-ish of screen
time.sleep(0.3)
pyautogui.keyDown("alt"); time.sleep(0.05)
pyautogui.keyDown("shift"); time.sleep(0.05)
pyautogui.press("v"); time.sleep(0.05)
pyautogui.keyUp("shift"); time.sleep(0.05)
pyautogui.keyUp("alt")
log("Voice keystroke sent")
time.sleep(3)
ss("a6_after_voice")

log("OK: STEP A DONE")


# ── Step B: Phone Link Call ─────────────────────────────────
log("")
log("=" * 60)
log("STEP B: PHONE LINK CALL")
log("=" * 60)

phone = "01280043725"

# B1: Kill existing Phone Link process + close windows
log("--- B1: Kill existing Phone Link ---")
import psutil
import pygetwindow as gw
for proc in psutil.process_iter(["pid", "name"]):
    if (proc.info.get("name") or "").lower() == "phoneexperiencehost.exe":
        log(f"  Killing PhoneExperienceHost PID={proc.info['pid']}")
        proc.kill()
        time.sleep(1)

wins = gw.getWindowsWithTitle(PHONE_LINK_TITLE)
if wins:
    log(f"Closing Phone Link window...")
    wins[0].close()
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if not gw.getWindowsWithTitle(PHONE_LINK_TITLE):
            break
        time.sleep(0.2)
    time.sleep(0.5)
else:
    log("No existing Phone Link window")
ss("b1_before_launch")

# B2: Launch Phone Link
log("--- B2: Launch Phone Link via shell:AppsFolder ---")
subprocess.Popen(["cmd", "/c", "start", "shell:AppsFolder\\Microsoft.YourPhone_8wekyb3d8bbwe!App"])
# Wait for splash screen first, then main window
pl_win = _wait_for_window("SplashScreen loading", timeout=10)
if pl_win:
    log(f"Splash screen found, waiting for full load...")
    time.sleep(5)  # let splash finish and main UI load
else:
    log("No splash screen, trying direct 'Link' title...")
pl_win = _wait_for_window(PHONE_LINK_TITLE, timeout=15)
if not pl_win:
    # Fallback: search by partial match
    log("Phone Link not found by title, searching all windows...")
    all_wins = gw.getAllWindows()
    for w in all_wins:
        t = w.title.lower()
        if 'phone' in t or 'link' in t or 'call' in t:
            log(f"  Found fallback: title={repr(w.title[:60])}")
            pl_win = w
            break
    if not pl_win:
        log("Still no Phone Link, taking screenshot of current state...")
        ss("b2_no_phonelink_fallback")
        (SCRIPT_DIR / "diagnose.log").write_text("\n".join(_log_lines))
        sys.exit(1)
log(f"Phone Link window found: title='{pl_win.title}' box={pl_win.box}")
time.sleep(2)
ss("b2_phonelink_opened")

# B3: Switch to Calls panel
log("--- B3: Switch to Calls panel (Ctrl+3) ---")
pl_win.activate()
time.sleep(0.3)
pyautogui.hotkey("ctrl", "3")
time.sleep(0.8)
ss("b3_calls_panel")

# B4: Type phone number
log(f"--- B4: Type phone number: {phone} ---")
pyautogui.typewrite(phone, interval=0.02)
# Let dialpad render
time.sleep(0.3)
ss("b4_number_typed")

# B5: Scroll down a bit
log("--- B5: Scroll down in Phone Link ---")
try:
    rect = pl_win.box
    cx = rect.left + rect.width // 2
    cy = rect.top + rect.height // 2
    pyautogui.moveTo(cx, cy)
    for _ in range(5):
        pyautogui.scroll(-1)
    time.sleep(0.3)
except Exception as e:
    log(f"Scroll failed: {e}")
ss("b5_after_scroll")

# B6: Find call button via template matching
log("--- B6: Template match call button ---")
pl_win.activate()
time.sleep(0.3)

# Full window screenshot
rect = pl_win.box
window_ss = pyautogui.screenshot(region=(rect.left, rect.top, rect.width, rect.height))
win_path = SCREENSHOT_DIR / "b6_phonelink_window.png"
window_ss.save(str(win_path))
log(f"[SS] Window screenshot saved: {win_path.name}")

if CALL_BUTTON_IMAGE.is_file():
    log(f"Template: {CALL_BUTTON_IMAGE.name} ({CALL_BUTTON_IMAGE.stat().st_size} bytes)")
    
    # Try multiple confidence levels
    for conf in [0.7, 0.55, 0.45, 0.35]:
        try:
            matches = list(pyautogui.locateAll(str(CALL_BUTTON_IMAGE), window_ss, confidence=conf))
            if matches:
                log(f"OK: Found {len(matches)} match(es) at conf={conf}")
                for i, m in enumerate(matches):
                    cx = rect.left + m.left + m.width // 2
                    cy = rect.top + m.top + m.height // 2
                    log(f"   Match {i+1}: screen_pos=({cx},{cy}), local=({m.left},{m.top}) size=({m.width}x{m.height})")
                    crop_path = crop_around(cx, cy, 200, f"call_match_conf{conf}_m{i+1}")
                break
            else:
                log(f"   No match at conf={conf}")
        except Exception as e:
            log(f"   Error at conf={conf}: {e}")

    # Now try with the best match we found
    best_match = None
    best_conf = None
    for conf in [0.7, 0.55, 0.45, 0.35]:
        try:
            matches = list(pyautogui.locateAll(str(CALL_BUTTON_IMAGE), window_ss, confidence=conf))
            if matches:
                best_match = matches[0]
                best_conf = conf
                break
        except:
            pass
    
    if best_match:
        click_x = rect.left + best_match.left + best_match.width // 2
        click_y = rect.top + best_match.top + best_match.height // 2
        log(f"--- B7: Clicking call button at ({click_x}, {click_y}) [conf={best_conf}] ---")
        
        # Pre-click crop
        crop_around(click_x, click_y, 200, "pre_click")
        
        pyautogui.click(click_x, click_y)
        time.sleep(1)
        
        # Post-click screenshots
        ss("b7_after_click")
        crop_around(click_x, click_y, 200, "post_click")
        
        log("OK: Call button clicked")
    else:
        log("FAIL: No match at any confidence level — trying Enter fallback")
        pyautogui.press("enter")
        time.sleep(1)
        ss("b7_enter_fallback")
else:
    log(f"FAIL: Template file missing: {CALL_BUTTON_IMAGE}")

# B8: Final state
log("--- B8: Final state ---")
ss("b8_final_state", region=(int(rect.left), int(rect.top), int(rect.width), int(rect.height)))

log("")
log("=" * 60)
log("DIAGNOSTIC COMPLETE")
log("=" * 60)

# Save log
log_path = SCRIPT_DIR / "diagnose.log"
log_path.write_text("\n".join(_log_lines))
log(f"Log saved to {log_path}")
