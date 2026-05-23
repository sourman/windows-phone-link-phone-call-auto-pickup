# auto-pickup

Automates **Perplexity Comet voice activation** + **Microsoft Phone Link call dialing**, triggered remotely via Telegram or SMS.

## Trigger flow

```
"COMET" message -> open Comet browser + voice mode -> dial phone via Phone Link
```

Two independent trigger entry points exist (run only one at a time):

1. **Telegram bot** (`telegram-comet-listener/listener.py`) — long-polls Telegram for "COMET" in private chats
2. **Queue watcher** (`queue-watcher/watcher.py`) — polls a Cloudflare Queue fed by `sms2queue` for SMS containing "COMET"

Both triggers call `pyautomation.py` functions directly.

## Automation layer

`pyautomation.py` is the sole automation backend (AHK removed). It uses:
- **UIA (UI Automation)** — for window discovery, control tree navigation, property reads, and Invoke patterns
- **PyAutoGUI** — for coordinate clicks, keyboard shortcuts, and mouse wheel scrolling
- **ctypes (Win32)** — for window foreground/maximize management

### Phone Link calling (UIA-based)
1. Find Phone Link window via UIA class name `WinUIDesktopWin32WindowClass`
2. Force foreground + maximize (order matters: foreground first, then maximize, because `_force_foreground` calls `SW_RESTORE` which undoes maximize)
3. `Ctrl+3` to switch to Calls/Dialer tab
4. UIA sanity check: verify `Keypad` control exists
5. `SetValue` on the contact search field (`AutoId=TextBox` inside `ContactSuggestionsBox`) — instant, no per-digit typing
6. `Enter` transfers the number from search to the dialer accumulator
7. Click the Call button via coordinates from UIA `BoundingRectangle`
8. Poll for call window (up to 10s) and verify "Send call to mobile device" button present (confirms call is on PC)

### Comet voice activation
- Kills existing Comet processes, launches two windows (fresh session trick), closes the first
- Navigates to URL via `Ctrl+L` + clipboard paste
- Activates voice mode via `Alt+Shift+V`

### End call
- `end_call()` finds the smaller Phone Link call window and invokes `EndCallButton` via UIA `Invoke` pattern

### CLI
```
python pyautomation.py comet [target_url]
python pyautomation.py call <phone_number>
python pyautomation.py endcall
python pyautomation.py both [target_url] [phone_number]
```

## UIA learnings and gotchas

- **Stale element references**: UIA element handles expire when the underlying window changes (resize, tab switch, new windows). Always re-find windows after layout changes. Wrap all property accesses (`ClassName`, `Name`, `BoundingRectangle`) in try/except — `COMError` is common.
- **`_find_by_autoid` skips notifications**: The Phone Link notification subtree has hundreds of controls. Skip `NotificationsList`, `PaneContent`, `MainContentGrid` etc. for 3x speedup.
- **Invoke pattern on dialpad buttons**: `IUIAutomationInvokePattern::Invoke()` causes a long-press on the `0` button (produces `+` instead of `0`). Use coordinate clicks instead. The Python library adds 0.5s sleep after each Invoke by default — pass `waitTime=0` to override.
- **Invoke on offscreen controls**: WinUI providers can reject `Invoke()` on offscreen buttons (Call button with `Rect=(0,0,0,0)` throws `COMError`). Scroll into view first or use coordinate-based approaches.
- **Keyboard input doesn't reach the dialpad**: `pyautogui.typewrite()` sends keys to the focused element, which is the contact search field, not the dialpad. The dialpad only registers on-screen button clicks.
- **`typewrite` vs `SetValue`**: `SetValue` via UIA's `ValuePattern` is instant and doesn't require focus. Use it for the contact search field.
- **`_force_foreground` restores windows**: It calls `SW_RESTORE` which undoes maximize. Always call foreground FIRST, then maximize.
- **Call window**: When a call starts, Phone Link opens a second smaller window (~492x356) with `EndCallButton`, `MuteButton`, `KeypadToggleButton`, and transfer button. The main window stays open behind it.
- **COM retry**: `_get_root_children()` retries up to 3 times because `GetRootControl().GetChildren()` can throw transient `COMError` during window open/close.

## Key details

- **Phone number**: hardcoded as `01280043725` (matching the SIM in Phone Link)
- **Target URL**: read from `target_url.txt`
- **Comet path**: `%LOCALAPPDATA%\Perplexity\Comet\Application\comet.exe`
- **Comet fresh-session hack**: Comet (Electron) shares sessions across windows. The automation launches two windows, kills the first, keeping the second which starts clean.
- **Phone Link**: UWP app, window class `WinUIDesktopWin32WindowClass`, process `PhoneExperienceHost.exe`
- **Dialer state**: Read from `ButtonCall.Name` property — empty dial shows `""`, dialed number shows `"Call Dialed number X Y Z "`

## Config

- `.env.local` — `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_QUEUE_ID`, `CLOUDFLARE_API_TOKEN`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_USER_IDS` (comma-separated)
- `target_url.txt` — single line URL for Comet to open

## Deployment

Both trigger services run as **Windows scheduled tasks** (headless, `-NoConsole` flag for Telegram). Each has its own `venv` and `register_autostart.ps1` to set up the scheduled task. Log files live alongside each script.

### Restarting the listener after code changes

The Telegram listener has a 999-retry loop and won't pick up code changes automatically. To update:

1. Kill ALL Python processes running `listener.py` (the scheduled task `schtasks /End` only stops the task, not lingering processes):
   ```
   Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" | Where-Object { $_.CommandLine -like '*listener*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
   ```
2. Delete `.pyc` caches: `find . -name "pyautomation*.pyc" -delete`
3. Start fresh: `schtasks /Run /TN "\\TelegramWatcher-AutoPickup"`

## WSL note

The project lives at `/mnt/c/Users/ggg/projects/auto-pickup` (accessed via WSL). The Telegram listener runs natively on Windows Python.
