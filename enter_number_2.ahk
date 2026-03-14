; Step 2: Enter the phone number in Calls panel "Search your contacts" and press Enter
; Accepts phone number as CLI argument, with fallback to temp file

#Requires AutoHotkey v2.0
SendMode("Input")
SetWorkingDir(A_ScriptDir)

SetTitleMatchMode(2)

logFile := "call-on-sms.log"
tempPhoneFile := A_ScriptDir "\call-on-sms-phone.tmp"

FileAppend("Step 2 at " A_Now "`n", logFile)

; Get phone number from CLI argument (primary method) or temp file (fallback)
phone := ""
if (A_Args.Length > 0 && A_Args[1] != "") {
    phone := A_Args[1]
    FileAppend("Step 2: got phone from CLI arg: " phone "`n", logFile)
} else if (FileExist(tempPhoneFile)) {
    phone := Trim(FileRead(tempPhoneFile))
    FileAppend("Step 2: got phone from temp file: " phone "`n", logFile)
} else {
    FileAppend("Step 2: no phone number (no CLI arg and no temp file)`n", logFile)
    ExitApp(1)
}

if (phone = "") {
    FileAppend("Step 2: empty phone number`n", logFile)
    ExitApp(1)
}

if (!WinExist("Phone Link")) {
    FileAppend("Step 2: Phone Link not found, launching...`n", logFile)
    Run("ms-phone://")
    ; Wait for Phone Link to open (max 10 seconds)
    Loop 100 {
        if (WinExist("Phone Link")) {
            FileAppend("Step 2: Phone Link launched`n", logFile)
            break
        }
        Sleep(100)
    }
    if (!WinExist("Phone Link")) {
        FileAppend("Step 2: Phone Link failed to launch`n", logFile)
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
    FileAppend("Step 2: searching for call button image...`n", logFile)
    ; Call button image is 90x90, click center
    BUTTON_OFFSET_X := 45
    BUTTON_OFFSET_Y := 45

    ; Get active window bounds to confine search
    WinGetPos(&winX, &winY, &winW, &winH, "Phone Link")

    ; Search within Phone Link window only
    if (ImageSearch(&gx, &gy, winX, winY, winX + winW - 1, winY + winH - 1, "*30 " . callButtonImage)) {
        FileAppend("Step 2: found call button at " gx "," gy " - clicking`n", logFile)
        ; click the center of the call button
        Click(gx + BUTTON_OFFSET_X, gy + BUTTON_OFFSET_Y)
        Sleep(200)
        FileAppend("Step 2: clicked call button`n", logFile)
    } else {
        FileAppend("Step 2: call button image not found, falling back to Enter`n", logFile)
        Send("{Enter}")
    }
} else {
    FileAppend("Step 2: call button image not found at " callButtonImage ", using Enter`n", logFile)
    Send("{Enter}")
}

FileAppend("Step 2: done`n", logFile)
ExitApp(0)
