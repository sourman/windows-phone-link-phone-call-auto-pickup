; Step 3: Enter the phone number in Calls panel "Search your contacts" and press Enter
; Accepts phone number as CLI argument, with fallback to temp file

#Requires AutoHotkey v2.0
SendMode("Input")
SetWorkingDir(A_ScriptDir)

SetTitleMatchMode(2)

logFile := "call-on-sms.log"
tempPhoneFile := A_ScriptDir "\call-on-sms-phone.tmp"

FileAppend("Step 3 at " A_Now "`n", logFile)

; Get phone number from CLI argument (primary method) or temp file (fallback)
phone := ""
if (A_Args.Length > 0 && A_Args[1] != "") {
    phone := A_Args[1]
    FileAppend("Step 3: got phone from CLI arg: " phone "`n", logFile)
} else if (FileExist(tempPhoneFile)) {
    phone := Trim(FileRead(tempPhoneFile))
    FileAppend("Step 3: got phone from temp file: " phone "`n", logFile)
} else {
    FileAppend("Step 3: no phone number (no CLI arg and no temp file)`n", logFile)
    ExitApp(1)
}

if (phone = "") {
    FileAppend("Step 3: empty phone number`n", logFile)
    ExitApp(1)
}

if (!WinExist("Phone Link")) {
    FileAppend("Step 3: Phone Link not found`n", logFile)
    ExitApp(1)
}

WinActivate("Phone Link")
Sleep(300)
Send("^3")
Sleep(500)
Send(phone)
Sleep(500)

; Image search for the call button
CoordMode("Pixel", "Screen")
CoordMode("Mouse", "Screen")
callButtonImage := A_ScriptDir "\assets\call_button.png"

if (FileExist(callButtonImage)) {
    FileAppend("Step 3: searching for call button image...`n", logFile)
    ; Load image to get dimensions for center clicking
    pic := LoadPicture(callButtonImage)
    imgWidth := pic.OriginalWidth
    imgHeight := pic.OriginalHeight
    centerX := Floor(imgWidth / 2)
    centerY := Floor(imgHeight / 2)
    FileAppend("Step 3: call button image is " imgWidth "x" imgHeight ", center offset: " centerX "," centerY "`n", logFile)

    ; Search entire screen for call button
    if (ImageSearch(&gx, &gy, 0, 0, A_ScreenWidth - 1, A_ScreenHeight - 1, "*30 " . callButtonImage)) {
        FileAppend("Step 3: found call button at " gx "," gy " - clicking`n", logFile)
        ; click the center of the call button
        Click(gx + centerX, gy + centerY)
        Sleep(200)
        FileAppend("Step 3: clicked call button`n", logFile)
    } else {
        FileAppend("Step 3: call button image not found, falling back to Enter`n", logFile)
        Send("{Enter}")
    }
} else {
    FileAppend("Step 3: call button image not found at " callButtonImage ", using Enter`n", logFile)
    Send("{Enter}")
}

FileAppend("Step 3: done`n", logFile)
ExitApp(0)
