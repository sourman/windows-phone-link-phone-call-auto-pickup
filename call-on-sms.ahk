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
step3Script := A_ScriptDir "\open-comet-voice.ahk"

Timestamp() {
    months := ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    return months[A_Mon] " " A_MDay ", " A_Hour ":" A_Min ":" A_Sec
}

Log(msg) {
    global logFile
    FileAppend("[" Timestamp() "] " msg "`n", logFile)
}

Log("Orchestrator starting")

SetTitleMatchMode(2)

#p:: Pause()
#s:: Suspend()

; Main loop - simple orchestrator
loop {
    try {
        ; Call step 1 - RunWait blocks until step 1 exits
        ; Step 1 will loop internally until notification found, then exit
        Log("Orchestrator: Calling step 1...")
        exitCode := RunWait('"' step1Script '"')

        if (exitCode = 0) {
            Log("Orchestrator: Step 1 succeeded - reading phone number")

            ; Capture phone number from environment variable (set by baby)
            phone := EnvGet("AUTO_PICKUP_PHONE")
            if (phone = "" && FileExist(tempPhoneFile)) {
                phone := Trim(FileRead(tempPhoneFile))
            }

            if (phone = "") {
                Log("Orchestrator: ERROR - Failed to capture phone number from step 1")
                continue
            }

            Log("Orchestrator: Phone number captured: " phone)
            Log("Orchestrator: Calling Step 2...")

            ; Step 2: Enter phone number and initiate call
            exitCode := RunWait('"' step2Script '" "' phone '"')
            if (exitCode = 0) {
                Log("Orchestrator: Step 2 succeeded - sequence complete")
            } else {
                Log("Orchestrator: Step 2 failed with exit code " exitCode)
            }

            ; Step 3: Open comet voice
            Log("Orchestrator: Calling step 3...")
            exitCode := RunWait('"' step3Script '"')
            if (exitCode = 0) {
                Log("Orchestrator: Step 3 succeeded - opened comet voice")
            } else {
                Log("Orchestrator: Step 3 failed with exit code " exitCode)
            }

            ; Debounce - wait before starting next cycle
            Sleep(120000) ; 2 minutes between calls
        } else {
            Log("Orchestrator: Step 1 failed/timeout (exit code " exitCode "), retrying...")
            Sleep(1000)
        }
    } catch Error as e {
        Log("Orchestrator: Error: " e.Message)
        Sleep(1000)
    }
}
