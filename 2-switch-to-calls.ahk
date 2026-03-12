; Step 2: Get phone number from Phone Link (Messages view), write to file, switch to Calls panel (Ctrl+3)
; Run after step 1; Phone Link should be open on the TENEEN conversation.

#Requires AutoHotkey v2.0
SendMode("Input")
SetWorkingDir(A_ScriptDir)

SetTitleMatchMode(2)

logFile := "call-on-sms.log"
numberFile := A_ScriptDir "\call-on-sms-number.txt"
defaultNumberFile := A_ScriptDir "\call-on-sms-default-number.txt"

phoneLinkWin := "Phone Link ahk_class WinUIDesktopWin32WindowClass ahk_exe PhoneExperienceHost.exe"

FileAppend("Step 2 at " A_Now "`n", logFile)

hwnd := WinExist(phoneLinkWin)
if (!hwnd) {
    FileAppend("Step 2: Phone Link window not found (" phoneLinkWin ")`n", logFile)
    ExitApp(1)
}

WinActivate("ahk_id " hwnd)
Sleep(200)

winText := ""
try {
    winText := WinGetText("ahk_id " hwnd)
}
phone := ""
if (RegExMatch(winText, "\+\d[\d\s\-\(\)]{9,}", &m)) {
    raw := m[0]
    phone := "+" RegExReplace(raw, "\D", "")
} else if (RegExMatch(winText, "\d{10,}", &m))
    phone := m[0]

if (phone != "") {
    try {
        FileDelete(numberFile)
        FileAppend(phone, numberFile)
    }
    FileAppend("Step 2: wrote " phone ", switching to Calls (Ctrl+3)`n", logFile)
} else {
    FileAppend("Step 2: WinGetText has no phone (WinUI frame only)`n", logFile)
    if (FileExist(defaultNumberFile)) {
        defaultNum := Trim(FileRead(defaultNumberFile))
        if (defaultNum != "") {
            try {
                FileDelete(numberFile)
                FileAppend(defaultNum, numberFile)
            }
            FileAppend("Step 2: wrote default number`n", logFile)
        }
    }
}
FileAppend("Step 2: switching to Calls (Ctrl+3)`n", logFile)

if (!WinActive("ahk_id " hwnd))
    WinActivate("ahk_id " hwnd)
Sleep(200)
Send("^3")
Sleep(800)
ExitApp(0)
