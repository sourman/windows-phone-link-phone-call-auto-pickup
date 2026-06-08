<#
  watchdog-wrapper.ps1 — Infinite-retry wrapper for the Telegram COMET listener.

  Runs listener.py with -B (no bytecode cache) in an infinite loop.
  If the script exits for any reason, waits 2 minutes and restarts it.
  Captures stdout and stderr separately for crash diagnostics.

  Scheduled Task points here instead of directly at pythonw.exe.
  No UAC / admin needed.
#>

$ErrorActionPreference = "Stop"

$PythonExe = "C:\Users\ggg\projects\auto-pickup\telegram-comet-listener\venv\Scripts\python.exe"
$Script    = "C:\Users\ggg\projects\auto-pickup\telegram-comet-listener\listener.py"
$WorkDir   = "C:\Users\ggg\projects\auto-pickup\telegram-comet-listener"
$RetrySec  = 120

$logFile  = Join-Path $WorkDir "watchdog-wrapper.log"
$stderrFile = Join-Path $WorkDir "stderr.log"

function Write-Log($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$ts  $msg" | Out-File -FilePath $logFile -Encoding utf8 -Append
}

Write-Log "=== Watchdog wrapper started ==="
Write-Log "PID: $PID"
Write-Log "User: $env:USERNAME"
Write-Log "Machine: $env:COMPUTERNAME"
Write-Log "Python: $PythonExe"
Write-Log "Script: $Script"
Write-Log "WorkDir: $WorkDir"
Write-Log "Stderr will be captured to: $stderrFile"

# Verify python exists
if (-not (Test-Path $PythonExe)) {
    Write-Log "FATAL: Python not found at $PythonExe"
    exit 1
}

# Verify script exists
if (-not (Test-Path $Script)) {
    Write-Log "FATAL: Script not found at $Script"
    exit 1
}

while ($true) {
    $startTime = Get-Date
    $attemptTs = $startTime.ToString("yyyy-MM-dd HH:mm:ss")
    Write-Log "[$attemptTs] Launching listener.py -B -NoConsole ..."

    try {
        $proc = Start-Process -FilePath $PythonExe `
            -ArgumentList "-B","`"$Script`"","-NoConsole" `
            -WorkingDirectory $WorkDir `
            -PassThru -NoNewWindow `
            -RedirectStandardError $stderrFile
        $proc.WaitForExit()
        $exitCode = $proc.ExitCode
        $runDuration = (Get-Date) - $startTime
        $exitLabel = if ($null -eq $exitCode) { "<killed>" } else { $exitCode }
        Write-Log "listener.py exited with code $exitLabel after $($runDuration.ToString('hh\:mm\:ss'))"

        # Append stderr contents to main log if non-empty
        if (Test-Path $stderrFile) {
            $stderrContent = Get-Content $stderrFile -Raw -ErrorAction SilentlyContinue
            if ($stderrContent -and $stderrContent.Trim()) {
                Write-Log "--- STDERR from listener.py ---"
                # Write each stderr line to log with timestamp
                foreach ($line in (Get-Content $stderrFile -ErrorAction SilentlyContinue)) {
                    Write-Log "  STDERR: $line"
                }
                Write-Log "--- END STDERR ---"
            }
        }
    } catch {
        Write-Log "ERROR: Failed to launch or monitor listener.py: $($_.Exception.Message)"
    }

    Write-Log "Waiting $RetrySec seconds before restart ..."
    Start-Sleep -Seconds $RetrySec
}
