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

; Click the search/number input field in the dialer (right panel)
; Phone Link window is maximized: the dialer search box is at roughly
; 85% of window width, 25% of window height
WinGetPos(&wx, &wy, &ww, &wh, "Phone Link")
searchX := wx + Round(ww * 0.85)
searchY := wy + Round(wh * 0.25)
Log("Clicking search field at " searchX "," searchY " (window " wx "," wy "," ww "," wh ")")
Click(searchX, searchY)
Sleep(500)

; Clear any existing text and type the phone number
Log("Typing phone number: " phone)
Send("^a")
Sleep(100)
Send(phone)
Sleep(500)

; Press Enter to initiate the call
Log("Pressing Enter to call")
Send("{Enter}")
Sleep(500)

Log("Done")
ExitApp(0)
