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

; Track existing Comet windows
existing := WinGetList("ahk_exe comet.exe")
Log("Existing windows and their ahk_ids: " existing.Length)
ids := ""
for hwnd in existing
    ids .= "ahk_id " hwnd ", "
Log("Current window IDs: " RTrim(ids, ", "))

; Launch Comet
LocalAppData := EnvGet("LOCALAPPDATA")
cometPath := LocalAppData "\Perplexity\Comet\Application\comet.exe"
try {
    pid := Run('"' cometPath '"')
} catch Error as e {
    Log("Failed to start Comet: " e.Message)
    ExitApp
}

; Wait for a new Comet window distinct from any already open
newHwnd := 0
timeoutMs := 15000
start := A_TickCount
while ((A_TickCount - start) < timeoutMs) {
    Sleep(2500) ; In testing found that any sleep time less than 1 second gives false data as the
    ; window is not available immediately
    current := WinGetList("ahk_exe comet.exe")
    Log("Current windows: " current.Length)
    ids := ""
    for hwnd in current
        ids .= "ahk_id " hwnd ", "
    Log("Current window IDs: " RTrim(ids, ", "))
    for hwnd in current {
        if !existing.Has(hwnd) {
            Log("New window found with ahk_id: " hwnd)
            newHwnd := hwnd
            break
        }
    }
    if (newHwnd) {
        break
    }
}

if (!newHwnd) {
    Log("No new window found after " (A_TickCount - start) "ms")
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
    Log("Could not find the newly opened Comet window.")
    ExitApp
}

; Activate the new window and wait until it's active
Sleep(200)
WinActivate("ahk_id " newHwnd)
Log("Activating window with ahk_id: " newHwnd)
if !WinWaitActive("ahk_id " newHwnd, , 10) {
    Log("Comet window did not become active.")
    ExitApp
}

; Send Alt+Shift+V to enable comet voice mode
Send("!+v")


ExitApp