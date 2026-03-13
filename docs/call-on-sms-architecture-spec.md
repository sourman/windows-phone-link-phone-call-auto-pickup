# Call-on-SMS Architecture Specification

## Overview
Chain of AutoHotkey scripts that automatically place a call when a TENEEN SMS notification is detected.

## Current Architecture

### Data Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│ call-on-sms.ahk (Orchestrator)                                         │
│ - Waits for TENEEN notification via OCR detection                      │
│ - Runs steps 1-2 sequentially                                          │
│ - Captures phone number from step 1 via EnvSet/temp file              │
│ - Passes phone number to step 2 as CLI arg                            │
└─────────────────────────────────────────────────────────────────────────┘
         │
         ├──► click_notification_1.ahk
         │     - OCR detection finds TENEEN notification
         │     - Click notification → opens Phone Link to Messages view
         │     - Extract phone number from Phone Link window text via OCR
         │     - Store via EnvSet("AUTO_PICKUP_PHONE") + temp file fallback
         │     - ExitApp(0) with number available
         │
         └──► enter_number_3.ahk "<PHONE_NUMBER>"
               - Activate Phone Link window
               - Send Ctrl+3 to switch to Calls panel
               - Check A_Args[1] for phone number (primary)
               - Fall back to temp file if arg empty (fallback)
               - Type phone number in Search field
               - Press Enter (this initiates the call)
```

### Component Responsibilities

| Script | Input | Output | Responsibility |
|--------|-------|--------|-----------------|
| **call-on-sms.ahk** | None | Coordinates execution | Orchestrator - waits for notification, runs steps 1-2, captures phone from step 1, passes to step 2 |
| **click_notification_1.ahk** | None | EnvVar + temp file | Click notification, extract phone from Phone Link window via OCR, store number |
| **enter_number_3.ahk** | CLI arg (phone) | None | Switch to Calls panel, type phone number, press Enter (initiates call) |

### Data Passing Mechanism

**Primary:** Environment Variable
```ahk
; Step 1 writes:
EnvSet("AUTO_PICKUP_PHONE", "+16478525107")

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
RunWait('"' A_ScriptDir '\enter_number_3.ahk" "' phone '"')

; Step 2 reads:
if (A_Args.Length > 0)
    phone := A_Args[1]
else
    phone := FileRead(tempFile)  ; fallback
```

## Implementation Details

### 1. click_notification_1.ahk
**Purpose:** Click notification and extract phone number

**Implementation:**
- OCR detection finds TENEEN notification on screen
- Clicks notification at OCR-detected coordinates
- Waits for Phone Link to open
- Captures Phone Link window header via screenshot + OCR
- Regex match for phone patterns: `\d{10,}` then formats as `+{digits}`
- Store via `EnvSet("AUTO_PICKUP_PHONE", phone)`
- Write to temp file `call-on-sms-phone.tmp` as fallback
- Log extraction success/failure

### 2. enter_number_3.ahk
**Purpose:** Switch to Calls panel and enter phone number

**Implementation:**
- Check `A_Args[1]` for phone number first (primary method)
- Fall back to reading `call-on-sms-phone.tmp` if arg empty
- Activate Phone Link window
- Send Ctrl+3 to switch to Calls panel
- Type phone number in Search field
- Press Enter (initiates the call)

### 3. call-on-sms.ahk (Orchestrator)
**Purpose:** Detect notification and coordinate execution

**Implementation:**
- Runs OCR detection loop in top-right quadrant of screen
- When TENEEN notification found:
  - Click notification at OCR-detected coordinates
  - Wait for Phone Link to open
  - Run step 1 (`click_notification_1.ahk`)
  - Capture phone number from EnvGet or temp file
  - Run step 2 (`enter_number_3.ahk`) with phone as CLI arg

```ahk
; After step 1 completes, capture phone number:
phone := EnvGet("AUTO_PICKUP_PHONE")
if (phone = "" && FileExist(tempPhoneFile))
    phone := FileRead(tempPhoneFile)

; Pass phone number to step 2:
RunWait('"' A_ScriptDir '\enter_number_3.ahk" "' phone '"')
```

## Testing

### Manual Testing Steps
1. **Test step 1 independently:**
   ```powershell
   .\click_notification_1.ahk
   # Check that phone number is in EnvVar and temp file
   ```

2. **Test step 2 with CLI arg:**
   ```powershell
   .\enter_number_3.ahk "+16478525107"
   # Should switch to calls, type the number and press Enter
   ```

3. **Test full orchestrator:**
   ```powershell
   .\call-on-sms.ahk
   # Trigger TENEEN notification, verify full sequence executes
   ```

### Expected Behavior
- Step 1 extracts phone number from Phone Link conversation header
- Phone number is available via environment variable to orchestrator
- Orchestrator passes phone number to step 2 as CLI argument
- No file I/O dependency between steps (except temp file fallback)
- Individual steps can be tested in isolation with CLI args

## Benefits

1. **Reliability:** No race conditions from file I/O between steps
2. **Testability:** Each step can be tested independently with CLI args
3. **Simplicity:** Clear data ownership - orchestrator owns the phone number
4. **Robustness:** Fallback mechanism ensures compatibility
5. **PowerShell compatible:** Can trigger individual scripts from command line

## Notes

- Environment variables are process-local in Windows, so EnvSet in step 1 is visible to orchestrator (same process tree)
- Temp file fallback is needed for cases where EnvSet doesn't propagate (different process contexts)
- Phone number extraction from Phone Link uses WinGetText (faster than full OCR)
- Regex patterns handle both international format (+1 647-852-5107) and plain digits
