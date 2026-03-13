# Call-on-SMS Architecture Specification

## Overview
Chain of AutoHotkey scripts that automatically place a call when a TENEEN SMS notification is detected.

## Current State (To Be Refactored)
Current implementation uses file-based data passing (`call-on-sms-number.txt`) between step 2 and step 3, which is fragile and hard to test.

## Target Architecture

### Data Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│ call-on-sms.ahk (Orchestrator)                                         │
│ - Waits for TENEEN notification via image detection                    │
│ - Runs steps 1-4 sequentially                                          │
│ - Captures phone number from step 1 via EnvSet/temp file              │
│ - Passes phone number to step 3 as CLI arg                            │
└─────────────────────────────────────────────────────────────────────────┘
         │
         ├──► 1-click-notification.ahk
         │     - Click notification → opens Phone Link to Messages view
         │     - Extract phone number from Phone Link window text
         │     - Store via EnvSet("AUTO_PICKUP_PHONE") + temp file fallback
         │     - ExitApp(0) with number available
         │
         ├──► 2-switch-to-calls.ahk
         │     - Activate Phone Link window
         │     - Send Ctrl+3 to switch to Calls panel
         │     - (No phone number needed - removed extraction logic)
         │
         ├──► 3-enter-number.ahk "<PHONE_NUMBER>"
         │     - Check A_Args[1] for phone number (primary)
         │     - Fall back to temp file if arg empty (fallback)
         │     - Type phone number in Search field
         │     - Press Enter
         │
         └──► 4-place-call.ahk
               - Click green call button
               - (No phone number needed)
```

### Component Responsibilities

| Script | Input | Output | Responsibility |
|--------|-------|--------|-----------------|
| **call-on-sms.ahk** | None | Coordinates execution | Orchestrator - waits for notification, runs steps 1-4, captures phone from step 1, passes to step 3 |
| **1-click-notification.ahk** | None | EnvVar + temp file | Click notification, extract phone from Phone Link window, store number |
| **2-switch-to-calls.ahk** | None | None | Switch Phone Link to Calls panel (Ctrl+3) |
| **3-enter-number.ahk** | CLI arg (phone) | None | Type phone number and press Enter |
| **4-place-call.ahk** | None | None | Click call button |

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

**Step 3 receives via CLI arg:**
```ahk
; Orchestrator runs:
Run(A_ScriptDir "\3-enter-number.ahk " phone)

; Step 3 reads:
if (A_Args.Length > 0)
    phone := A_Args[1]
else
    phone := FileRead(tempFile)  ; fallback
```

## Implementation Changes

### 1. 1-click-notification.ahk
**Changes:**
- Add phone number extraction from Phone Link window after clicking notification
- Use `WinGetText()` to get window text content
- Regex match for phone patterns: `\+\d[\d\s\-\(\)]{9,}` or `\d{10,}`
- Store via `EnvSet("AUTO_PICKUP_PHONE", phone)`
- Write to temp file `call-on-sms-phone.tmp` as fallback
- Log extraction success/failure

**Removals:**
- None (new functionality)

### 2. 2-switch-to-calls.ahk
**Changes:**
- Remove phone number extraction logic entirely
- Simplify to just activate Phone Link and send Ctrl+3
- Remove file operations for phone number

**Removals:**
- All phone number extraction code
- References to `call-on-sms-number.txt`
- References to `call-on-sms-default-number.txt`

### 3. 3-enter-number.ahk
**Changes:**
- Check `A_Args[1]` for phone number first (primary method)
- Fall back to reading `call-on-sms-phone.tmp` if arg empty
- Remove old file-only approach using `call-on-sms-number.txt`

**Removals:**
- References to `call-on-sms-number.txt`
- References to `call-on-sms-default-number.txt`

### 4. 4-place-call.ahk
**Changes:**
- None (no data dependency)

**Removals:**
- None

### 5. call-on-sms.ahk (Orchestrator)
**Changes:**
- After step 1 completes, capture phone number:
  ```ahk
  Run(A_ScriptDir "\1-click-notification.ahk", , , &pid1)
  WaitPid(pid1)

  ; Capture phone number
  phone := EnvGet("AUTO_PICKUP_PHONE")
  if (phone = "" && FileExist(tempPhoneFile))
      phone := FileRead(tempPhoneFile)

  if (phone = "") {
      FileAppend("Failed to capture phone number`n", logFile)
      ExitApp(1)
  }
  ```
- Pass phone number to step 3:
  ```ahk
  Run(A_ScriptDir "\3-enter-number.ahk " phone)
  ```

**Removals:**
- None (orchestrator now owns data passing)

## Files to Delete
After implementation, these files are no longer needed:
- `call-on-sms-number.txt` (if exists)
- `call-on-sms-default-number.txt` (if exists)

## Testing

### Manual Testing Steps
1. **Test step 1 independently:**
   ```powershell
   .\1-click-notification.ahk
   # Check that phone number is in EnvVar and temp file
   ```

2. **Test step 3 with CLI arg:**
   ```powershell
   .\3-enter-number.ahk "+16478525107"
   # Should type the number and press Enter
   ```

3. **Test full orchestrator:**
   ```powershell
   .\call-on-sms.ahk
   # Trigger TENEEN notification, verify full sequence executes
   ```

### Expected Behavior
- Step 1 extracts phone number from Phone Link conversation header
- Phone number is available via environment variable to orchestrator
- Orchestrator passes phone number to step 3 as CLI argument
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
