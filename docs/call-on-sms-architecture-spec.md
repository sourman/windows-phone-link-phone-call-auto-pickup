# Call-on-SMS Architecture Specification

## Overview
Chain of AutoHotkey scripts that automatically place a call when a TENEEN SMS notification is detected.

## Current Architecture

### Data Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│ call-on-sms.ahk (Orchestrator)                                         │
│ - Loops continuously, calling step 1 via RunWait()                     │
│ - When step 1 exits successfully, reads phone number                   │
│ - Passes phone number to step 2 as CLI arg                            │
│ - No OCR detection in orchestrator - step 1 handles detection         │
└─────────────────────────────────────────────────────────────────────────┘
         │
         ├──► click_notification_1.ahk (Step 1)
         │     - Loops continuously scanning for TENEEN notification
         │     - OCR detection finds TENEEN notification
         │     - Click notification → opens Phone Link to Messages view
         │     - Publish phone number via EnvSet("AUTO_PICKUP_PHONE")
         │     - IMPORTANT: ExitApp(0) when done (does not loop forever)
         │     - Orchestrator's RunWait() unblocks when step 1 exits
         │
         └──► enter_number_2.ahk "<PHONE_NUMBER>" (Step 2)
               - Activate Phone Link window (launch if closed)
               - Send Ctrl+3 to switch to Calls panel
               - Check A_Args[1] for phone number (primary)
               - Fall back to temp file if arg empty (fallback)
               - Type phone number in Search field
               - Image search for call button → click, or fallback to Enter
```

### Component Responsibilities

| Script | Input | Output | Responsibility |
|--------|-------|--------|-----------------|
| **call-on-sms.ahk** | None | Coordinates execution | Simple orchestrator - loops calling step 1, reads phone number, passes to step 2 |
| **click_notification_1.ahk** | None | EnvVar + temp file | Loop to detect notification, click it, publish phone number, **EXIT** when done |
| **enter_number_2.ahk** | CLI arg (phone) | None | Switch to Calls panel, type phone number, press Enter/call button |

### Data Passing Mechanism

**Primary:** Environment Variable
```ahk
; Step 1 writes:
EnvSet("AUTO_PICKUP_PHONE", "+16479163598")

; Orchestrator reads:
phone := EnvGet("AUTO_PICKUP_PHONE")
```

**Fallback:** Temp File
```ahk
; Step 1 writes:
tempFile := A_ScriptDir "\call-on-sms-phone.tmp"
FileAppend(phone, tempFile)

; Orchestrator reads:
phone := FileRead(tempFile)
```

**Step 2 receives via CLI arg:**
```ahk
; Orchestrator runs:
RunWait('"' A_ScriptDir '\enter_number_2.ahk" "' phone '"')

; Step 2 reads:
if (A_Args.Length > 0)
    phone := A_Args[1]
else
    phone := FileRead(tempFile)  ; fallback
```

## Implementation Details

### 1. click_notification_1.ahk (Step 1)
**Purpose:** Detect notification, click it, and publish phone number

**Implementation:**
- Loops continuously scanning for TENEEN notification (OCR or image search)
- When found: clicks notification at detected coordinates
- Waits for Phone Link to open
- **IMPORTANT:** Does NOT loop forever - exits after successful click
- Publishes phone number via:
  - `EnvSet("AUTO_PICKUP_PHONE", phone)` (primary)
  - Temp file `call-on-sms-phone.tmp` (fallback)
- **Currently:** Phone number is hardcoded (`PHONE_NUMBER := "+16479163598"`) as a shortcut
- **TODO:** Extract phone number from Phone Link window via OCR
- ExitApp(0) on success, ExitApp(1) on failure

### 2. enter_number_2.ahk
**Purpose:** Switch to Calls panel and initiate call

**Implementation:**
- Check `A_Args[1]` for phone number first (primary method)
- Fall back to reading `call-on-sms-phone.tmp` if arg empty
- Activate Phone Link window (launch via `ms-phone://` if not running)
- Send Ctrl+3 to switch to Calls panel
- Type phone number in Search field
- Image search for call button (assets/call_button.png) and click center
- Fallback to Enter if image not found
- ExitApp(0) on success

### 3. call-on-sms.ahk (Orchestrator)
**Purpose:** Coordinate execution between step 1 and step 2

**Implementation:**
- Simple loop - no OCR detection in orchestrator
- Calls step 1 via `RunWait()` - blocks until step 1 exits
- If step 1 succeeds (exit code 0):
  - Capture phone number from EnvGet or temp file
  - Run step 2 (`enter_number_2.ahk`) with phone as CLI arg
- If step 1 fails, loop continues

```ahk
; Main loop:
loop {
    exitCode := RunWait('"' A_ScriptDir '\click_notification_1.ahk"')
    if (exitCode = 0) {
        ; Step 1 found notification, clicked, and published phone
        phone := EnvGet("AUTO_PICKUP_PHONE")
        if (phone = "" && FileExist(tempPhoneFile))
            phone := FileRead(tempPhoneFile)
        ; Pass to step 2:
        RunWait('"' A_ScriptDir '\enter_number_2.ahk" "' phone '"')
    }
    Sleep(1000)
}
```

## Testing

### Manual Testing Steps
1. **Test step 1 independently:**
   ```powershell
   .\click_notification_1.ahk
   # Should loop until TENEEN notification appears, then click and exit
   # Check that phone number is in EnvVar and temp file after exit
   ```

2. **Test step 2 with CLI arg:**
   ```powershell
   .\enter_number_2.ahk "+16479163598"
   # Should switch to calls, type the number and press Enter
   ```

3. **Test full orchestrator:**
   ```powershell
   .\call-on-sms.ahk
   # Trigger TENEEN notification, verify full sequence executes
   ```

### Expected Behavior
- Step 1 (click_notification_1.ahk) loops until TENEEN notification found
- When found: clicks notification, publishes phone number (currently hardcoded), exits
- Orchestrator's RunWait() unblocks, reads phone number from step 1
- Orchestrator passes phone to step 2 as CLI argument
- Step 2 activates Phone Link, switches to Calls, types number, initiates call
- Individual steps can be tested in isolation with CLI args

## Benefits

1. **Reliability:** No race conditions from file I/O between steps
2. **Testability:** Each step can be tested independently with CLI args
3. **Simplicity:** Clear data ownership - orchestrator owns the phone number
4. **Robustness:** Fallback mechanism ensures compatibility
5. **PowerShell compatible:** Can trigger individual scripts from command line

## Notes

- **Orchestrator is dumb/simple** - just loops calling step 1, no detection logic
- **Step 1 does all the work** - detection, clicking, publishing phone, then exits
- RunWait() blocking is intentional - orchestrator waits for step 1 to finish
- Environment variables are process-local in Windows, so EnvSet in step 1 is visible to orchestrator (same process tree)
- Temp file fallback is needed for cases where EnvSet doesn't propagate (different process contexts)
- **Phone number is currently hardcoded** as shortcut (`+16479163598`), OCR extraction TODO
