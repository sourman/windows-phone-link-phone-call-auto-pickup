# Auto Phone Call Pick Up using Microsoft Phone Link with AutoHotkey

Automatically answer incoming calls on Microsoft Phone Link and open Perplexity voice mode in Comet browser.

## Quick Start

1. **Find window info**: Run `find-windows.ahk` when receiving a call to identify button names
2. **Start automation**: Run `auto-pickup.ahk` with Phone Link open
3. **Adjust settings**: Edit the script based on what you discover in step 1

## Files

- `auto-pickup.ahk` - Main automation script (auto-answers calls and opens Perplexity)
- `find-windows.ahk` - Helper script to identify window names and controls
- `setup-guide.md` - Detailed setup and troubleshooting instructions

### Call on SMS (TENEEN → call back)

- `call-on-sms.ahk` - Loop: image-match TENEEN notification, then run steps 1–4
- `1-click-notification.ahk` - Click the notification (opens Phone Link to Messages)
- `2-switch-to-calls.ahk` - Read number from Phone Link, write to `call-on-sms-number.txt`, send Ctrl+3
- `3-enter-number.ahk` - Type number in Search your contacts, Enter
- `4-place-call.ahk` - Click green call button

**Assets (in `assets/`):** `notification-teneen.png` (crop of the Messages popup with TENEEN), `call-button.png` (crop of the green call button in Calls panel). Test each step script on its own.

## Controls

- `Win+P` - Pause/resume script
- `Win+S` - Suspend/resume hotkey detection

See `setup-guide.md` for detailed instructions.