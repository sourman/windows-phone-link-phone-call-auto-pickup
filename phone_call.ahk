; Step: Activate Phone Link via Win+7, switch to Calls, type number, click call button
; Accepts phone number as CLI argument

#Requires AutoHotkey v2.0
SendMode("Input")
SetWorkingDir(A_ScriptDir)

logFile := "phone_call.log"

Timestamp() {
    months := ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    return months[A_Mon] " " A_MDay ", " A_Hour ":" A_Min ":" A_Sec
}

Log(msg) {
    global logFile
    FileAppend("[" Timestamp() "] " msg "`n", logFile)
}

Log("Starting phone call")

; Get phone number from CLI argument
if (A_Args.Length > 0 && A_Args[1] != "") {
    phone := A_Args[1]
    Log("Got phone from CLI arg: " phone)
} else {
    Log("No phone number provided")
    ExitApp(1)
}

; Activate Phone Link via taskbar shortcut (Win+7)
Log("Win+7 to activate Phone Link")
Send("#7")
Sleep(2000)

; Make sure Phone Link is in the foreground
if (!WinExist("Phone Link")) {
    Log("Phone Link window not found after Win+7")
    ExitApp(1)
}

WinActivate("Phone Link")
Sleep(500)

; Switch to Calls panel with Ctrl+3
Log("Switching to Calls panel (Ctrl+3)")
Send("^3")
Sleep(1000)

; Type the phone number
Log("Typing phone number: " phone)
Send(phone)
Sleep(500)

; Move mouse into Phone Link window and scroll down
WinGetPos(&wx, &wy, &ww, &wh, "Phone Link")
MouseMove(wx + ww // 2, wy + wh // 2)
Loop 5
    Click("WheelDown")
Sleep(300)

; Image search for the call button
CoordMode("Pixel", "Screen")
CoordMode("Mouse", "Screen")
callButtonImage := A_ScriptDir "\assets\call_button-gray.png"

if (FileExist(callButtonImage)) {
    Log("Searching for call button image...")
    BUTTON_OFFSET_X := 40
    BUTTON_OFFSET_Y := 35

    WinGetPos(&winX, &winY, &winW, &winH, "Phone Link")

    if (ImageSearch(&gx, &gy, winX, winY, winX + winW - 1, winY + winH - 1, "*70 " . callButtonImage)) {
        Log("Found call button at " gx "," gy " - clicking")
        Click(gx + BUTTON_OFFSET_X, gy + BUTTON_OFFSET_Y)
        Sleep(200)
        Log("Clicked call button")
    } else {
        Log("Call button image not found, falling back to Enter")
        Send("{Enter}")
    }
} else {
    Log("Call button image not found at " callButtonImage ", using Enter")
    Send("{Enter}")
}

Log("Done")
ExitApp(0)
