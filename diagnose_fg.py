"""Diagnose foreground issue + force-minimize everything except PL."""
import sys
sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', errors='replace', closefd=False)

import ctypes
import time
import subprocess

# What IS in foreground?
fg = ctypes.windll.user32.GetForegroundWindow()
print(f"Current FG HWND: {fg}")

# Get its window info
buf = ctypes.create_unicode_buffer(256)
ctypes.windll.user32.GetWindowTextW(fg, buf, 256)
print(f"FG Window Title: '{buf.value}'")

# Get class name
ctypes.windll.user32.GetClassNameW(fg, buf, 256)
print(f"FG Class: '{buf.value}'")

# Get PL rect to see if Comet overlaps
import uiautomation as auto
pl = None
for c in auto.GetRootControl().GetChildren():
    if "phone link" in (c.Name or "").lower():
        pl = c
        break

if pl:
    r = pl.BoundingRectangle
    print(f"\nPL rect: [{r.left},{r.top},{r.right},{r.bottom}]")
    print(f"PL HWND: {pl.NativeWindowHandle}")
    
    # Is PL even visible/restoreable?
    style = ctypes.windll.user32.GetWindowLongW(pl.NativeWindowHandle, -16)  # GWL_STYLE
    print(f"PL GWL_STYLE: {style} (minimized={bool(style & 0x20000000}) visible={bool(style & 0x10000000)})")

# List ALL top-level windows with their Z-order (top to bottom)
print("\n--- Z-order top to bottom ---")
hwnd = ctypes.windll.user32.GetTopWindow(None)
count = 0
while hwnd and count < 20:
    ctypes.windll.user32.GetWindowTextW(hwnd, buf, 256)
    title = buf.value[:50]
    ctypes.windll.user32.GetClassNameW(hwnd, buf, 256)
    cls = buf.value[:30]
    is_visible = ctypes.windll.user32.IsWindowVisible(hwnd)
    is_fg = (hwnd == fg)
    marker = " <<< FG" if is_fg else ""
    print(f"  [{count}] HWND={hwnd} vis={is_visible} class='{cls}' title='{title}'{marker}")
    hwnd = ctypes.windll.user32.GetWindow(hwnd, 3)  # GW_HWNDNEXT
    count += 1

# Now try: Minimize ALL windows except PL, then show PL
print("\n--- Force-minimizing non-PL windows ---")
result = subprocess.run([
    "powershell.exe", "-Command", """
Add-Type @'
using System; using System.Runtime.InteropServices;
public class WinUtil {
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
}
'@

$targetHwnd = $args[0]

Get-Process | Where-Object { $_.MainWindowHandle -ne 0 } | ForEach-Object {
    $h = $_.MainWindowHandle
    if ($h -ne $targetHwnd -and [WinUtil]::IsWindowVisible($h)) {
        $title = $_.MainWindowTitle
        Write-Output "Minimizing: $($_.ProcessName) ($title)"
        [WinUtil]::ShowWindow($h, 6)  # SW_MINIMIZE
    }
}

Start-Sleep -Milliseconds 500
Write-Output "Done minimizing"
""", str(pl.NativeWindowHandle)
], capture_output=True, text=True, timeout=10)
print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)

time.sleep(1)

# Now check FG again
fg2 = ctypes.windll.user32.GetForegroundWindow()
print(f"\nAfter minimize - FG HWND: {fg2}")

# Try SetForegroundWindow now
print("Trying SetForegroundWindow...")
ret = ctypes.windll.user32.SetForegroundWindow(pl.NativeWindowHandle)
print(f"SetForegroundWindow result: {ret}")

time.sleep(0.5)
fg3 = ctypes.windll.user32.GetForegroundWindow()
print(f"After SFFW - FG HWND: {fg3} (match={fg3==pl.NativeWindowHandle})")
