#Requires AutoHotkey v2.0

logFile := "C:\Users\USER\workspace\auto-pickup\test-simple.log"
capturePath := "C:\Users\USER\workspace\auto-pickup\capture.png"
ocrScript := "C:\Users\USER\workspace\auto-pickup\o.ps1"
tmpPhoneFile := "C:\Users\USER\workspace\auto-pickup\call-on-sms-phone.tmp"

FileAppend("=== START ===`n", logFile)

Sleep(3000)
FileAppend("Clicking...`n", logFile)

w := A_ScreenWidth
h := A_ScreenHeight
Click(w - 300, h - 250)

Sleep(3000)
FileAppend("Finding Phone Link...`n", logFile)

win := "ahk_exe PhoneExperienceHost.exe"
if (WinExist(win)) {
    FileAppend("Phone Link found!`n", logFile)
    WinActivate(win)
    Sleep(1000)

    WinGetPos(&x, &y, &ww, &wh, win)
    FileAppend("Window: " x "," y "," ww "," wh "`n", logFile)

    psCmd := "Add-Type -AssemblyName System.Windows.Forms,System.Drawing; "
    psCmd .= "$bmp = [System.Drawing.Bitmap]::new(" . ww . ",150); "
    psCmd .= "$g = [System.Drawing.Graphics]::FromImage($bmp); "
    psCmd .= "$g.CopyFromScreen(" . x . "," . y . ",0,0); "
    psCmd .= "$bmp.Save('" . capturePath . "'); $g.Dispose(); $bmp.Dispose()"

    RunWait('PowerShell.exe -Command "' . psCmd . '"', , "Hide")
    FileAppend("Captured`n", logFile)

    psOCR := "Add-Type -AssemblyName System.Runtime.WindowsRuntime;"
    psOCR .= "[Windows.Media.Ocr.OcrEngine,Windows,ContentType=WindowsRuntime]|Out-Null;"
    psOCR .= "[Windows.Graphics.Imaging.BitmapDecoder,Windows,ContentType=WindowsRuntime]|Out-Null;"
    psOCR .= "$b=[System.Drawing.Bitmap]::new('" . capturePath . "');"
    psOCR .= "$s=[System.IO.MemoryStream]::new();"
    psOCR .= "$b.Save($s,[System.Drawing.Imaging.ImageFormat]::Png);"
    psOCR .= "$s.Position=0;"
    psOCR .= "$d=[Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($s).GetAwaiter().GetResult();"
    psOCR .= "$f=$d.GetFrameAsync(0).GetAwaiter().GetResult();"
    psOCR .= "$e=[Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages();"
    psOCR .= "$r=$e.RecognizeAsync($f).GetAwaiter().GetResult();"
    psOCR .= "$r.Text"

    FileDelete(ocrScript)
    FileAppend(psOCR, ocrScript, "UTF-8")

    shell := ComObject("WScript.Shell")
    exec := shell.Exec("PowerShell.exe -ExecutionPolicy Bypass -File " . ocrScript)

    ocrText := ""
    while (!exec.StdOut.AtEndOfStream) {
        ocrText .= exec.StdOut.ReadAll()
    }

    FileAppend("OCR: [" ocrText . "]`n", logFile)

    phone := ""
    if (RegExMatch(ocrText, "\d{10,}", &m))
        phone := m[0]

    if (phone != "") {
        phone := "+" . RegExReplace(phone, "\D", "")
        FileAppend("PHONE: " phone "`n", logFile)
        EnvSet("AUTO_PICKUP_PHONE", phone)
        FileDelete(tmpPhoneFile)
        FileAppend(phone, tmpPhoneFile)
        FileAppend("SUCCESS!`n", logFile)
    }
} else {
    FileAppend("Phone Link NOT found`n", logFile)
}

FileAppend("=== END ===`n", logFile)
ExitApp(0)
