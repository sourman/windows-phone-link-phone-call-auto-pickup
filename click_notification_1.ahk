; AutoHotkey v2 script to detect and click notifications in bottom-right corner
; Monitors for Windows-style toasts and clicks them when found
; When found: clicks notification, publishes phone number, then exits

#Requires AutoHotkey v2.0
#SingleInstance Force
SendMode("Input")
SetWorkingDir(A_ScriptDir)

; Improve reliability detecting transient/hosted windows
DetectHiddenWindows(true)
SetWinDelay(0)

; Create or overwrite log file
logFile := "call-on-sms.log"
tempPhoneFile := A_ScriptDir "\call-on-sms-phone.tmp"
PHONE_NUMBER := "+16479163598"  ; TODO: Extract via OCR instead of hardcoded

FileAppend("Step 1 starting at " A_Now "`n", logFile)

; Match window titles partially
SetTitleMatchMode(2)

; Use screen coordinates for pixel/mouse ops
CoordMode("Pixel", "Screen")
CoordMode("Mouse", "Screen")

; Template image for notification detection (grayscale for color-insensitive shape matching)
NotificationImage := A_ScriptDir "\assets\notification-teneen-gray.png"

; Set up hotkeys for manual control
#p:: Pause()
#s:: Suspend()


; Track last detection to avoid spam clicking
LastDetectionTime := 0
DEBOUNCE_MS := 3000  ; Wait 3 seconds between detections

loop {
    try {
        if (FileExist(NotificationImage)) {
            CurrentTime := A_TickCount
            if ((CurrentTime - LastDetectionTime) > DEBOUNCE_MS) {

                ; Search region: bottom-right quadrant of screen
                monW := A_ScreenWidth
                monH := A_ScreenHeight

                ; Start from right side, bottom 30% of screen
                startX := Floor(monW * 0.7)
                startY := Floor(monH * 0.7)

                FileAppend("Searching region: (" startX "," startY ") to (" monW "," monH ")`n", logFile)

                ; ImageSearch options for shape/color-insensitive matching:
                ; *150 - shades of variation (0-255). Higher = more color tolerant
                ;        150 allows moderate color variation while maintaining shape matching
                ; *TransBlack - makes black pixels match any color (handles anti-aliasing/edges)
                ;
                ; Notes: *255 would match ALL colors (shape-only), but increases false positives
                ;        150 is a good balance for notifications that may vary by theme/light-dark mode
                if (ImageSearch(&foundX, &foundY, startX, startY, monW - 1, monH - 1, "*150 *TransBlack " . NotificationImage)) {
                    FileAppend("NOTIFICATION FOUND at " foundX "," foundY " - clicking...`n", logFile)

                    LastDetectionTime := CurrentTime

                    ; Click the notification
                    Click(foundX, foundY)

                    FileAppend("Clicked notification`n", logFile)
                    Sleep(500)

                    ; Wait for Phone Link to open
                    Sleep(1500)

                    ; Publish phone number via EnvSet (primary method)
                    try {
                        EnvSet("AUTO_PICKUP_PHONE", PHONE_NUMBER)
                        FileAppend("Step 1: Set AUTO_PICKUP_PHONE env var`n", logFile)
                    } catch as e {
                        FileAppend("Step 1: EnvSet failed: " e.Message "`n", logFile)
                    }

                    ; Fallback: write to temp file
                    try {
                        if (FileExist(tempPhoneFile))
                            FileDelete(tempPhoneFile)
                        FileAppend(PHONE_NUMBER, tempPhoneFile)
                        FileAppend("Step 1: Wrote phone to temp file: " PHONE_NUMBER "`n", logFile)
                    } catch as e {
                        FileAppend("Step 1: Temp file write failed: " e.Message "`n", logFile)
                    }

                    ; SUCCESS - Exit with code 0 so orchestrator's RunWait returns
                    FileAppend("Step 1: Done, exiting with success`n`n", logFile)
                    ExitApp(0)
                } else {
                    FileAppend(".", logFile)  ; Dot per scan for activity indicator
                }
            }
        } else {
            FileAppend("WARNING: Notification image not found: " NotificationImage "`n", logFile)
        }
    } catch Error as e {
        FileAppend("Error: " e.Message "`n", logFile)
    }
    Sleep(500)  ; Check twice per second
}
