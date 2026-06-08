import ctypes, time

u = ctypes.windll.user32
k = ctypes.windll.kernel32

pl_hwnd = 1115566

# Step 1: Find ALL visible top-level windows and their threads
print("=== Enumerating windows ===")
hwnd = u.GetTopWindow(None)
count = 0
windows = []
while hwnd and count < 30:
    buf = ctypes.create_unicode_buffer(256)
    u.GetWindowTextW(hwnd, buf, 256)
    title = buf.value[:60]
    vis = u.IsWindowVisible(hwnd)
    tid = u.GetWindowThreadProcessId(hwnd, None)
    pid = ctypes.c_ulong()
    u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    
    marker = ""
    if "phone" in title.lower():
        marker = " <<< PHONE LINK"
    if "comet" in title.lower():
        marker = " <<< COMET"
    
    print(f"  [{count}] HWND={hwnd} vis={vis} tid={tid} pid={pid.value} '{title}'{marker}")
    windows.append((hwnd, tid, title, vis))
    
    hwnd = u.GetWindow(hwnd, 3)  # GW_HWNDNEXT
    count += 1

# Step 2: Try AttachThreadInput with EACH visible window's thread
print("\n=== Trying AttachThreadInput with each visible window ===")
our_tid = k.GetCurrentThreadId()
print(f"Our TID={our_tid}")

for wh, wt, wtitle, wvis in windows:
    if not wvis:
        continue
    try:
        u.AttachThreadInput(wt, our_tid, True)
        time.sleep(0.05)
        
        # Now try SetForegroundWindow on PL
        u.ShowWindow(pl_hwnd, 9)  # SW_RESTORE
        result = u.SetForegroundWindow(pl_hwnd)
        
        time.sleep(0.3)
        new_fg = u.GetForegroundWindow()
        
        u.AttachThreadInput(wt, our_tid, False)
        
        status = "WIN!" if new_fg == pl_hwnd else f"fg={new_fg}"
        print(f"  Via '{wtitle[:30]}' (tid={wt}): SFFW={result} -> {status}")
        
        if new_fg == pl_hwnd:
            print("\n*** PHONE LINK IS NOW IN FOREGROUND ***")
            break
    except Exception as e:
        print(f"  Via '{wtitle[:30]}' ERROR: {e}")

# Final check
time.sleep(0.5)
final = u.GetForegroundWindow()
buf = ctypes.create_unicode_buffer(256)
u.GetWindowTextW(final, buf, 256)
print(f"\nFinal FG HWND={final} Title='{buf.value}'")
