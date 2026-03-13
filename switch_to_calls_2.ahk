; Step 2: Activate Phone Link and switch to Calls panel (Ctrl+3)
; Phone number extraction now happens in step 1

#Requires AutoHotkey v2.0
SendMode("Input")
SetWorkingDir(A_ScriptDir)

SetTitleMatchMode(2)

logFile := "call-on-sms.log"

phoneLinkWin := "Phone Link ahk_class WinUIDesktopWin32WindowClass ahk_exe PhoneExperienceHost.exe"

FileAppend("Step 2 at " A_Now "`n", logFile)

hwnd := WinExist(phoneLinkWin)
if (!hwnd) {
    FileAppend("Step 2: Phone Link window not found (" phoneLinkWin ")`n", logFile)
    ExitApp(1)
}

WinActivate("ahk_id " hwnd)
Sleep(300)

; Switch to Calls panel with Ctrl+3
Send("^3")
Sleep(800)
FileAppend("Step 2: switched to Calls panel (Ctrl+3)`n", logFile)

ExitApp(0)
