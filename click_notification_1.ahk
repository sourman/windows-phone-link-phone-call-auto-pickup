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

logFile := "call-on-sms.log"
tempPhoneFile := A_ScriptDir "\call-on-sms-phone.tmp"
PHONE_NUMBER := "01280043725"  ; TODO: Extract via OCR instead of hardcoded
DEBUG_MODE := false

Timestamp() {
    months := ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    return months[A_Mon] " " A_MDay ", " A_Hour ":" A_Min ":" A_Sec
}

Log(msg) {
    global logFile
    FileAppend("[" Timestamp() "] " msg "`n", logFile)
}

Log("Step 1 starting")

; Match window titles partially
SetTitleMatchMode(2)

; Use screen coordinates for pixel/mouse ops
CoordMode("Pixel", "Screen")
CoordMode("Mouse", "Screen")

; Template image for notification detection (grayscale for color-insensitive shape matching)
NotificationImage := A_ScriptDir "\assets\TENEEN.png"

; Track last detection to avoid spam clicking
LastDetectionTime := 0
DEBOUNCE_MS := 3000  ; Wait 3 seconds between detections

loop {
    try {
        if (FileExist(NotificationImage)) {
            CurrentTime := A_TickCount
            if ((CurrentTime - LastDetectionTime) > DEBOUNCE_MS) {

                ; Search region: focused rectangle in bottom-right corner
                monW := A_ScreenWidth
                monH := A_ScreenHeight

                ; Constrained search rectangle (10% × 10% in bottom-right)
                startX := Floor(monW * 0.78)  ; 80.5%
                startY := Floor(monH * 0.75)  ; 77.3%
                endX   := startX + 200
                endY   := startY + 100

                if (DEBUG_MODE) {
                    Log("Step 1: Searching region: (" startX "," startY ") to (" endX "," endY ")")
                }

                ; ImageSearch options for shape/color-insensitive matching:
                ; *150 - shades of variation (0-255). Higher = more color tolerant
                ;        150 allows moderate color variation while maintaining shape matching
                ; *TransBlack - makes black pixels match any color (handles anti-aliasing/edges)
                ;
                ; Notes: *255 would match ALL colors (shape-only), but increases false positives
                ;        150 is a good balance for notifications that may vary by theme/light-dark mode
                if (ImageSearch(&foundX, &foundY, startX, startY, endX, endY,  NotificationImage)) {
                    Log("NOTIFICATION FOUND at " foundX "," foundY " - clicking...")

                    LastDetectionTime := CurrentTime

                    ; Click the notification
                    Click(foundX, foundY)

                    Log("Clicked notification")
                    Sleep(500)

                    ; Wait for Phone Link to open
                    Sleep(1500)

                    ; TODO, Detect the phone number that sent the SMS using OCR

                    ; Publish phone number via EnvSet (primary method)
                    try {
                        EnvSet("AUTO_PICKUP_PHONE", PHONE_NUMBER)
                        Log("Step 1: Set AUTO_PICKUP_PHONE env var")
                    } catch as e {
                        Log("Step 1: EnvSet failed: " e.Message)
                    }

                    ; Fallback: write to temp file
                    try {
                        if (FileExist(tempPhoneFile))
                            FileDelete(tempPhoneFile)
                        FileAppend(PHONE_NUMBER, tempPhoneFile)
                        Log("Step 1: Wrote phone to temp file: " PHONE_NUMBER)
                    } catch as e {
                        Log("Step 1: Temp file write failed: " e.Message)
                    }

                    ; SUCCESS - Exit with code 0 so orchestrator's RunWait returns
                    Log("Step 1: Done, exiting with success")
                    ExitApp(0)
                } else if (DEBUG_MODE) {
                    Log(".")  ; Dot per scan for activity indicator
                }
                ; sleep for a bit to slow down CPU usage
                Sleep(2000)
            }
        } else {
            Log("WARNING: Notification image not found: " NotificationImage)
        }
    } catch Error as e {
        Log("Error: " e.Message)
    }
    Sleep(500)  ; Check twice per second
}
