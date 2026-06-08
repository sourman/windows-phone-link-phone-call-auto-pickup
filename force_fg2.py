"""Force FG — test all known SetForegroundWindow bypass methods."""
import ctypes
import ctypes.wintypes
import time
import sys

u = ctypes.windll.user32
k = ctypes.windll.kernel32

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# --- Properly-sized INPUT struct for SendInput (64-bit) ---
class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long), ("dy", ctypes.c_long),
                ("mouseData", ctypes.wintypes.DWORD), ("dwFlags", ctypes.wintypes.DWORD),
                ("time", ctypes.wintypes.DWORD), ("dwExtraInfo", ctypes.c_ulonglong)]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", ctypes.wintypes.WORD), ("wScan", ctypes.wintypes.WORD),
                ("dwFlags", ctypes.wintypes.DWORD), ("time", ctypes.wintypes.DWORD),
                ("dwExtraInfo", ctypes.c_ulonglong)]

class _INPUT_UNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT)]

class INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.wintypes.DWORD), ("_anon", _INPUT_UNION)]

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
VK_MENU = 0x12

def _send_alt():
    """Send ALT press/release via SendInput (modern API)."""
    down = INPUT(type=INPUT_KEYBOARD)
    down._anon.ki.wVk = VK_MENU
    up = INPUT(type=INPUT_KEYBOARD)
    up._anon.ki.wVk = VK_MENU
    up._anon.ki.dwFlags = KEYEVENTF_KEYUP
    u.SendInput(2, (INPUT * 2)(down, up), ctypes.sizeof(INPUT))

# --- Find Phone Link HWND dynamically ---
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
pl_hwnd = None

def enum_cb(hwnd, lp):
    global pl_hwnd
    buf = ctypes.create_unicode_buffer(256)
    u.GetWindowTextW(hwnd, buf, 256)
    if "phone link" in buf.value.lower():
        pl_hwnd = hwnd
        print(f"  Found Phone Link: HWND={hwnd}")
    return True

print("=== Finding Phone Link ===")
u.EnumWindows(WNDENUMPROC(enum_cb), 0)

if not pl_hwnd:
    print("ERROR: Phone Link window not found!")
    sys.exit(1)

print(f"Phone Link HWND={pl_hwnd}")

# --- Method 1: SendInput ALT trick ---
def method1_sendinput_alt(hwnd):
    print("\n--- Method 1: SendInput ALT trick ---")
    _send_alt()
    time.sleep(0.05)
    u.ShowWindow(hwnd, 9)
    r = u.SetForegroundWindow(hwnd)
    time.sleep(0.3)
    fg = u.GetForegroundWindow()
    print(f"  SFW={r} fg={fg} {'SUCCESS!' if fg == hwnd else 'nope'}")
    return fg == hwnd

# --- Method 2: keybd_event ALT trick ---
def method2_keybd_alt(hwnd):
    print("\n--- Method 2: keybd_event ALT trick ---")
    u.keybd_event(VK_MENU, 0, 0, 0)
    u.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
    time.sleep(0.05)
    u.ShowWindow(hwnd, 9)
    r = u.SetForegroundWindow(hwnd)
    time.sleep(0.3)
    fg = u.GetForegroundWindow()
    print(f"  SFW={r} fg={fg} {'SUCCESS!' if fg == hwnd else 'nope'}")
    return fg == hwnd

# --- Method 3: AllocConsole/FreeConsole trick ---
def method3_alloc_console(hwnd):
    print("\n--- Method 3: AllocConsole/FreeConsole trick ---")
    k.AllocConsole()
    con_hwnd = k.GetConsoleWindow()
    u.SetWindowPos(con_hwnd, 0, 0, 0, 0, 0, 0x0400)  # SWP_NOACTIVATE
    k.FreeConsole()
    u.ShowWindow(hwnd, 9)
    r = u.SetForegroundWindow(hwnd)
    time.sleep(0.3)
    fg = u.GetForegroundWindow()
    print(f"  SFW={r} fg={fg} {'SUCCESS!' if fg == hwnd else 'nope'}")
    return fg == hwnd

# --- Method 4: SPI_SETFOREGROUNDLOCKTIMEOUT trick ---
def method4_spi_timeout(hwnd):
    print("\n--- Method 4: SPI timeout trick ---")
    old = ctypes.c_int()
    u.SystemParametersInfoW(0x2000, 0, ctypes.byref(old), 0)
    print(f"  Current timeout: {old.value}ms")
    zero = ctypes.c_int(0)
    u.SystemParametersInfoW(0x2001, 0, ctypes.byref(zero), 2)
    u.ShowWindow(hwnd, 9)
    r = u.SetForegroundWindow(hwnd)
    time.sleep(0.3)
    fg = u.GetForegroundWindow()
    u.SystemParametersInfoW(0x2001, 0, ctypes.byref(old), 2)  # restore
    print(f"  SFW={r} fg={fg} {'SUCCESS!' if fg == hwnd else 'nope'}")
    return fg == hwnd

# --- Method 5: AttachThreadInput trick ---
def method5_attach_thread(hwnd):
    print("\n--- Method 5: AttachThreadInput trick ---")
    our_tid = k.GetCurrentThreadId()
    fg_tid = u.GetWindowThreadProcessId(u.GetForegroundWindow(), None)
    target_tid = u.GetWindowThreadProcessId(hwnd, None)
    print(f"  our_tid={our_tid} fg_tid={fg_tid} target_tid={target_tid}")
    u.AttachThreadInput(fg_tid, our_tid, True)
    u.AttachThreadInput(target_tid, our_tid, True)
    u.ShowWindow(hwnd, 9)
    r = u.SetForegroundWindow(hwnd)
    time.sleep(0.3)
    fg = u.GetForegroundWindow()
    u.AttachThreadInput(fg_tid, our_tid, False)
    u.AttachThreadInput(target_tid, our_tid, False)
    print(f"  SFW={r} fg={fg} {'SUCCESS!' if fg == hwnd else 'nope'}")
    return fg == hwnd

# --- Method 6: Nuclear — ALT + SPI + AttachThreadInput ---
def method6_nuclear(hwnd):
    print("\n--- Method 6: Nuclear (ALT + SPI + AttachThreadInput) ---")
    # Zero the timeout
    old = ctypes.c_int()
    u.SystemParametersInfoW(0x2000, 0, ctypes.byref(old), 0)
    u.SystemParametersInfoW(0x2001, 0, ctypes.byref(ctypes.c_int(0)), 2)
    # Send ALT
    _send_alt()
    time.sleep(0.05)
    # Attach threads
    our_tid = k.GetCurrentThreadId()
    fg_tid = u.GetWindowThreadProcessId(u.GetForegroundWindow(), None)
    target_tid = u.GetWindowThreadProcessId(hwnd, None)
    u.AttachThreadInput(fg_tid, our_tid, True)
    u.AttachThreadInput(target_tid, our_tid, True)
    # Go
    u.ShowWindow(hwnd, 9)
    u.BringWindowToTop(hwnd)
    r = u.SetForegroundWindow(hwnd)
    time.sleep(0.3)
    fg = u.GetForegroundWindow()
    # Cleanup
    u.AttachThreadInput(fg_tid, our_tid, False)
    u.AttachThreadInput(target_tid, our_tid, False)
    u.SystemParametersInfoW(0x2001, 0, ctypes.byref(old), 2)
    print(f"  SFW={r} fg={fg} {'SUCCESS!' if fg == hwnd else 'nope'}")
    return fg == hwnd

# --- Run all methods ---
print("\n=== Current foreground ===")
fg_before = u.GetForegroundWindow()
buf = ctypes.create_unicode_buffer(256)
u.GetWindowTextW(fg_before, buf, 256)
print(f"  FG HWND={fg_before} Title='{buf.value}'")

methods = [method1_sendinput_alt, method2_keybd_alt, method3_alloc_console,
           method4_spi_timeout, method5_attach_thread, method6_nuclear]
for method in methods:
    if method(pl_hwnd):
        print(f"\n*** {method.__name__} WORKED! ***")
        break
    time.sleep(0.5)
else:
    print("\n*** All methods failed! ***")

print("\n=== Final state ===")
fg_final = u.GetForegroundWindow()
u.GetWindowTextW(fg_final, buf, 256)
print(f"  FG HWND={fg_final} Title='{buf.value}'")
