#Requires AutoHotkey v2.0
#SingleInstance Force
#WinActivateForce
SendMode("Input")
SetWorkingDir(A_ScriptDir)

logFile := "comet-voice-close.log"

Timestamp() {
    months := ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    return months[A_Mon] " " A_MDay ", " A_Hour ":" A_Min ":" A_Sec
}

Log(msg) {
    global logFile
    FileAppend("[" Timestamp() "] " msg "`n", logFile)
}

Log("Step 3 starting")

; Close all existing Comet windows
existing := WinGetList("ahk_exe comet.exe")
Log("Found " existing.Length " existing Comet window(s)")
for hwnd in existing {
    WinClose("ahk_id " hwnd)
    Log("Closed window with ahk_id: " hwnd)
}

; Wait for all windows to close
if (existing.Length > 0) {
    Sleep(1000)
}

; HACK: Comet doesn't provide a flag to launch a fresh session.
; We work around this by launching two windows and killing the first one,
; which forces the second window to start with a clean session.
;
; NOTE: Comet is an Electron app that can have multiple windows per process.
; The windows share the same ahk_pid but have different ahk_id values.
; This means we can't just wait for "ahk_exe comet.exe" - we need to wait
; for the window COUNT to increase, since WinWait returns immediately if
; ANY Comet window already exists.
; Launch first Comet window
LocalAppData := EnvGet("LOCALAPPDATA")
cometPath := LocalAppData "\Perplexity\Comet\Application\comet.exe"
try {
    Run('"' cometPath '"')
} catch Error as e {
    Log("Failed to start first Comet: " e.Message)
    ExitApp
}

; Wait for the first Comet window to appear
if !WinWait("ahk_exe comet.exe", , 10) {
    Log("First Comet window did not appear within 10 seconds")
    ExitApp
}

; Get the first window handle immediately after it appears
firstList := WinGetList("ahk_exe comet.exe")
if (firstList.Length = 0) {
    Log("Could not find first Comet window after launch")
    ExitApp
}
firstHwnd := firstList[1]
Log("Found first Comet window with ahk_id: " firstHwnd)

Sleep(5000)

; Debug: Check how many windows we have before second launch
beforeSecondLaunch := WinGetList("ahk_exe comet.exe")
Log("Windows before second launch: " beforeSecondLaunch.Length)

; Launch second Comet window
Log("Attempting to launch second Comet window...")
try {
    Run('"' cometPath '"')
    Log("Second Comet Run() executed successfully")
} catch Error as e {
    Log("Failed to start second Comet: " e.Message)
    ExitApp
}

; Wait for the second Comet window to appear (wait for 2 windows total)
startTime := A_TickCount
while (A_TickCount - startTime < 10000) {
    currentList := WinGetList("ahk_exe comet.exe")
    if (currentList.Length >= 2) {
        break
    }
    Sleep(100)
}

; Check if we got 2 windows
currentList := WinGetList("ahk_exe comet.exe")
if (currentList.Length < 2) {
    Log("Could not find two Comet windows after launch. Only found: " currentList.Length)
    ExitApp
}
Log("Windows after second launch: " currentList.Length)

; Get both window handles and find the NEW one (the second window)
secondList := WinGetList("ahk_exe comet.exe")
if (secondList.Length < 2) {
    Log("Could not find two Comet windows after launch")
    ExitApp
}

; Find the window that wasn't in the first list
secondHwnd := ""
for hwnd in secondList {
    if (hwnd != firstHwnd) {
        secondHwnd := hwnd
        break
    }
}

if (secondHwnd = "") {
    Log("Could not identify second Comet window")
    ExitApp
}

Log("Found second Comet window with ahk_id: " secondHwnd)

; Kill the first window
WinClose("ahk_id " firstHwnd)
Log("Closed first window with ahk_id: " firstHwnd)

; Wait for window to close
Sleep(500)

; Activate the second window and wait until it's active
WinActivate("ahk_id " secondHwnd)
Log("Activating second window with ahk_id: " secondHwnd)
if !WinWaitActive("ahk_id " secondHwnd, , 10) {
    Log("Second Comet window did not become active.")
    ExitApp
}

; Send Alt+Shift+V to enable comet voice mode
Send("!+v")


ExitApp