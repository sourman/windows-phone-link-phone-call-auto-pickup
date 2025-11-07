#Requires AutoHotkey v2.0
#SingleInstance Force
SendMode("Input")
SetWorkingDir(A_ScriptDir)

; Create or overwrite log file
logFile := "comet-voice-close.log"
FileAppend("Starting script at " A_Now "`n`n", logFile)

; Track existing Comet windows
existing := WinGetList("ahk_exe comet.exe")
FileAppend("Existing windows and their ahk_ids in one go: " existing.Length "`n`n", logFile)
FileAppend("Current window IDs: ", logFile)
for hwnd in existing
    FileAppend("ahk_id " hwnd ", ", logFile)
FileAppend("`n`n", logFile)

; Launch Comet
cometPath := "C:\\Users\\USER\\AppData\\Local\\Perplexity\\Comet\\Application\\comet.exe"
try {
    pid := Run('"' cometPath '"')
} catch Error as e {
    FileAppend("Failed to start Comet: " e.Message "`n`n", logFile)
    ExitApp
}

; Wait for a new Comet window distinct from any already open
newHwnd := 0
timeoutMs := 15000
start := A_TickCount
while ((A_TickCount - start) < timeoutMs) {
    Sleep(2000) ; In testing foud that any sleep time less than 1 second gives fals data s the
    ; window is not available immediately
    current := WinGetList("ahk_exe comet.exe")
    FileAppend("Current windows and their ahk_ids in one go: " current.Length "`n`n", logFile)
    FileAppend("Current window IDs: ", logFile)
    for hwnd in current
        FileAppend("ahk_id " hwnd ", ", logFile)
    FileAppend("`n`n", logFile)
    for hwnd in current {
        if !existing.Has(hwnd) {
            FileAppend("New window found with ahk_id: " hwnd "`n`n", logFile)
            newHwnd := hwnd
            break
        }
    }
    if (newHwnd) {
        break
    }
}

if (!newHwnd) {
    FileAppend("No new window found after " (A_TickCount - start) "ms`n`n", logFile)
    ; Fallback to pid mapping (in case there were no prior windows)
    if (existing.Length = 0) {
        WinWait("ahk_exe comet.exe", , 10)
        list := WinGetList("ahk_exe comet.exe")
        if (list.Length > 0) {
            newHwnd := list[1]
        }
    }
}

if (!newHwnd) {
    FileAppend("Could not find the newly opened Comet window.`n`n", logFile)
    ExitApp
}

; Activate the new window and wait until it's active
WinActivate("ahk_id " newHwnd)
FileAppend("Activating window with ahk_id: " newHwnd "`n`n", logFile)
if !WinWaitActive("ahk_id " newHwnd, , 10) {
    FileAppend("Comet window did not become active.`n`n", logFile)
    ExitApp
}

; Send Alt+Shift+V
Send("!+v")

; Wait 10 seconds
Sleep(10000)

; Close only the window we opened
WinClose("ahk_id " newHwnd)
WinWaitClose("ahk_id " newHwnd, , 5)

FileAppend("We should have closed comet by now. the ahk_id is " newHwnd "`n`n", logFile)

Sleep(10000)

ExitApp