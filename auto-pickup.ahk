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
    try {
        if (FileExist(IncomingCallImage)) {
            CurrentTime := A_TickCount
            if ((CurrentTime - LastCallTime) > 5000) {
                monW := A_ScreenWidth, monH := A_ScreenHeight
                startX := Floor(monW * 0.5)
                startY := Floor(monH * 0.2)
                if (ImageSearch(&gx, &gy, startX, startY, monW - 1, monH - 1, "*90 " . IncomingCallImage)) {
                    TrayTip("Incoming Call Detected!", "Global image match - answering...", 2)
                    FileAppend("Global image search matched at " gx "," gy " - answering...`n", logFile)
                    LastCallTime := CurrentTime
                    Click(gx, gy)
                    FileAppend("Clicked global match at " gx "," gy "`n`n", logFile)
                    Sleep(500)
                } else {
                    FileAppend("Global image search no match this cycle`n", logFile)
                }
            }
        }
    } catch Error as e {
        FileAppend("Global image search error: " e.Message "`n", logFile)
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
