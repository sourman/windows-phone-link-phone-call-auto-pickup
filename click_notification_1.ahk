#Requires AutoHotkey v2.0

logFile := "C:\Users\USER\workspace\auto-pickup\test-simple.log"

FileAppend("START`n", logFile)
FileAppend("Screen: " A_ScreenWidth "x" A_ScreenHeight "`n", logFile)
FileAppend("Done`n", logFile)

ExitApp(0)
