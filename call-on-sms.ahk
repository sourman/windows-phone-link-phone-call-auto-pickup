; Call on SMS - Orchestrator
; Loops continuously, calling step 1 to detect notification
; When step 1 exits successfully, reads phone number and calls step 2
; Step 1 handles all detection logic - orchestrator is dumb/simple

#Requires AutoHotkey v2.0
#SingleInstance Force
SendMode("Input")
SetWorkingDir(A_ScriptDir)

logFile := "call-on-sms.log"
tempPhoneFile := A_ScriptDir "\call-on-sms-phone.tmp"
step1Script := A_ScriptDir "\click_notification_1.ahk"
step2Script := A_ScriptDir "\enter_number_2.ahk"

FileAppend("Mama starting at " A_Now "`n`n", logFile)

SetTitleMatchMode(2)

#p:: Pause()
#s:: Suspend()

TrayTip("Call on SMS", "Orchestrator running - waiting for step 1 to find notification...", 2)

; Main loop - simple orchestrator
loop {
    try {
        ; Call step 1 - RunWait blocks until step 1 exits
        ; Step 1 will loop internally until notification found, then exit
        FileAppend("Orchestrator: Calling step 1...`n", logFile)
        exitCode := RunWait('"' step1Script '"')

        if (exitCode = 0) {
            FileAppend("Orchestrator: Step 1 succeeded - reading phone number`n", logFile)

            ; Capture phone number from environment variable (set by baby)
            phone := EnvGet("AUTO_PICKUP_PHONE")
            if (phone = "" && FileExist(tempPhoneFile)) {
                phone := Trim(FileRead(tempPhoneFile))
            }

            if (phone = "") {
                FileAppend("Orchestrator: ERROR - Failed to capture phone number from step 1`n", logFile)
                continue
            }

            FileAppend("Orchestrator: Phone number captured: " phone "`n", logFile)
            FileAppend("Orchestrator: Calling Step 2...`n", logFile)

            ; Step 2: Enter phone number and initiate call
            exitCode := RunWait('"' step2Script '" "' phone '"')
            if (exitCode = 0) {
                FileAppend("Orchestrator: Step 2 succeeded - sequence complete`n`n", logFile)
            } else {
                FileAppend("Orchestrator: Step 2 failed with exit code " exitCode "`n", logFile)
            }

            ; Debounce - wait before starting next cycle
            Sleep(8000)
        } else {
            FileAppend("Orchestrator: Step 1 failed/timeout (exit code " exitCode "), retrying...`n", logFile)
            Sleep(1000)
        }
    } catch Error as e {
        FileAppend("Orchestrator: Error: " e.Message "`n", logFile)
        Sleep(1000)
    }
}
