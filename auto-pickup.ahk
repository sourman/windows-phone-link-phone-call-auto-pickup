; AutoHotkey v2 script to auto-answer incoming calls on Phone Link and open Perplexity voice mode on Comet
; Make sure Phone Link is running before starting this script

#Requires AutoHotkey v2.0
#SingleInstance Force
SendMode("Input")
SetWorkingDir(A_ScriptDir)

; Improve reliability detecting transient/hosted windows (e.g., Win11 toasts)
DetectHiddenWindows(true)
SetWinDelay(0)

; Create or overwrite log file
logFile := "auto-pickup.log"
FileAppend("Starting script at " A_Now "`n`n", logFile)

; Match window titles partially
SetTitleMatchMode(2)

; Use screen coordinates for pixel/mouse ops
CoordMode("Pixel", "Screen")
CoordMode("Mouse", "Screen")

; Template image to positively identify the Phone Link incoming call toast
IncomingCallImage := A_ScriptDir "\assets\incoming_call.png"

; Set up hotkeys for manual control
#p:: Pause()
#s:: Suspend()

TrayTip("Auto Pickup", "Script Started - Waiting for incoming calls...", 2)

; Track if we've already answered a call to avoid multiple triggers
LastCallTime := 0
CallWindowFound := false

loop {
    ; Enumerate likely Win11 toast host windows instead of relying on the generic title
    try {
        candidates := []
        ; Primary host on Win10/11
        ; Collect unique window handles from all toast-hosting sources
        for hwnd in WinGetList("ahk_class Windows.UI.Core.CoreWindow")
            candidates.Push(hwnd)
        for hwnd in WinGetList("ahk_exe ShellExperienceHost.exe")
            if !candidates.Has(hwnd)
                candidates.Push(hwnd)
        for hwnd in WinGetList("ahk_class XamlExplorerHostIslandWindow ahk_exe ShellExperienceHost.exe")
            if !candidates.Has(hwnd)
                candidates.Push(hwnd)
        for hwnd in WinGetList("ahk_class Xaml_WindowedPopupClass ahk_exe ShellExperienceHost.exe")
            if !candidates.Has(hwnd)
                candidates.Push(hwnd)

        if (candidates.Length > 0) {
            FileAppend("Found " candidates.Length " toast candidates`n", logFile)
            FileAppend("Toast candidate IDs: ", logFile)
            for hwnd in candidates
                FileAppend(hwnd ", ", logFile)
            FileAppend("`n`n", logFile)
            CurrentTime := A_TickCount
            for hwnd in candidates {
                if (isWindowCloaked(hwnd)) {
                    FileAppend("Toast candidate hwnd=" hwnd " is cloaked`n", logFile)
                    continue
                }

                WinGetPos(&x, &y, &w, &h, "ahk_id " hwnd)
                ; Heuristic: toast typically in bottom-right quadrant with dimensions similar to spy sample
                if (w < 200 || h < 100) {
                    FileAppend("Toast candidate hwnd=" hwnd " is too small: " w "x" h "`n", logFile)
                    continue
                }
                FileAppend("Toast candidate hwnd=" hwnd " at " x "," y " " w "x" h "`n", logFile)

                ; Optional region filter (bottom-right of primary monitor)
                monW := A_ScreenWidth, monH := A_ScreenHeight
                if (x < monW * 0.5 && y < monH * 0.4) {
                    FileAppend("Toast candidate hwnd=" hwnd " is in NOT in bottom-right quadrant: " x "," y "`n", logFile)
                    continue
                }

                FileAppend("Toast candidate hwnd=" hwnd " at " x "," y " " w "x" h "`n", logFile)

                if ((CurrentTime - LastCallTime) <= 5000) {
                    FileAppend("Toast candidate hwnd=" hwnd " is too recent: " (CurrentTime - LastCallTime) "ms`n", logFile)
                    continue
                }

                if (FileExist(IncomingCallImage) && ImageSearch(&fx, &fy, x, y, x + w, y + h, "*90 " .
                    IncomingCallImage)) {
                    TrayTip("Incoming Call Detected!", "Matched image - answering...", 2)
                    FileAppend("Matched image in hwnd=" hwnd " - answering...`n", logFile)
                    LastCallTime := CurrentTime

                    Click(x + w / 2, y + h / 2)
                    FileAppend("Clicked toast center at " x + w / 2 "," y + h / 2 "`n`n", logFile)
                    Sleep(500)
                    break
                } else {
                    FileAppend("No positive image match in hwnd=" hwnd "; skipping`n", logFile)
                }
            }
        }
    }
    Sleep(1000) ; run this loop only once every second
}

; Returns true if the window is cloaked (not visually shown) by DWM
isWindowCloaked(hwnd) {
    static DWMWA_CLOAKED := 14
    cloaked := 0
    ; DwmGetWindowAttribute(hwnd, DWMWA_CLOAKED, &cloaked, sizeof(cloaked))
    if (DllCall("dwmapi.dll\DwmGetWindowAttribute", "ptr", hwnd, "int", DWMWA_CLOAKED, "ptr", Buf := Buffer(4, 0),
    "int", 4) = 0) {
        cloaked := NumGet(Buf, 0, "UInt")
        return (cloaked != 0)
    }
    return false
}
