; Step 2: Enter the phone number in Calls panel "Search your contacts" and press Enter
; Accepts phone number as CLI argument, with fallback to temp file

#Requires AutoHotkey v2.0
SendMode("Input")
SetWorkingDir(A_ScriptDir)

SetTitleMatchMode(2)

logFile := "call-on-sms.log"
tempPhoneFile := A_ScriptDir "\call-on-sms-phone.tmp"

Timestamp() {
    months := ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    return months[A_Mon] " " A_MDay ", " A_Hour ":" A_Min ":" A_Sec
}

Log(msg) {
    global logFile
    FileAppend("[" Timestamp() "] " msg "`n", logFile)
}

Log("Step 2 starting")

; Get phone number from CLI argument (primary method) or temp file (fallback)
phone := ""
if (A_Args.Length > 0 && A_Args[1] != "") {
    phone := A_Args[1]
    Log("Step 2: got phone from CLI arg: " phone)
} else if (FileExist(tempPhoneFile)) {
    phone := Trim(FileRead(tempPhoneFile))
    Log("Step 2: got phone from temp file: " phone)
} else {
    Log("Step 2: no phone number (no CLI arg and no temp file)")
    ExitApp(1)
}

if (phone = "") {
    Log("Step 2: empty phone number")
    ExitApp(1)
}

if (!WinExist("Phone Link")) {
    Log("Step 2: Phone Link not found, launching...")
    Run("ms-phone://")
    ; Wait for Phone Link to open (max 10 seconds)
    Loop 100 {
        if (WinExist("Phone Link")) {
            Log("Step 2: Phone Link launched")
            break
        }
        Sleep(100)
    }
    if (!WinExist("Phone Link")) {
        Log("Step 2: Phone Link failed to launch")
        ExitApp(1)
    }
    Sleep(1000)  ; Give it extra time to fully load
}

WinActivate("Phone Link")
Sleep(300)
Send("^3")
Sleep(500)
Send(phone)
Sleep(500)

; Scroll down to make the call button visible at bottom of window
Send("{PgDn}")
Sleep(300)

; Image search for the call button
CoordMode("Pixel", "Screen")
CoordMode("Mouse", "Screen")
callButtonImage := A_ScriptDir "\assets\call_button.png"

if (FileExist(callButtonImage)) {
    Log("Step 2: searching for call button image...")
    ; Call button image is 90x90, click center
    BUTTON_OFFSET_X := 45
    BUTTON_OFFSET_Y := 45

    ; Get active window bounds to confine search
    WinGetPos(&winX, &winY, &winW, &winH, "Phone Link")

    ; Search within Phone Link window only
    if (ImageSearch(&gx, &gy, winX, winY, winX + winW - 1, winY + winH - 1, "*30 " . callButtonImage)) {
        Log("Step 2: found call button at " gx "," gy " - clicking")
        ; click the center of the call button
        Click(gx + BUTTON_OFFSET_X, gy + BUTTON_OFFSET_Y)
        Sleep(200)
        Log("Step 2: clicked call button")
    } else {
        Log("Step 2: call button image not found, falling back to Enter")
        Send("{Enter}")
    }
} else {
    Log("Step 2: call button image not found at " callButtonImage ", using Enter")
    Send("{Enter}")
}

Log("Step 2: done")
ExitApp(0)
