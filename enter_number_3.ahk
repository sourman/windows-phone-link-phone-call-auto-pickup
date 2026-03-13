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
Sleep(100)
Send("{Enter}")
FileAppend("Step 3: sent number and Enter`n", logFile)
ExitApp(0)
