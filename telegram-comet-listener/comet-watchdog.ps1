# comet-watchdog.ps1 - Bulletproof watchdog for the COMET listener.
#
# Inspired by wsl-monitor-v2.ps1: lightweight check loop that monitors
# the listener's liveness file and restarts it if it dies.
#
# Escalation chain:
#   1. Restart listener.py (up to 3 consecutive attempts)
#   2. After 3 failures: launch Claude Code to debug
#   3. If Claude Code fails: send Telegram alert to Teneen
#
# Deployment:
#   - Task Scheduler runs this at logon, hidden, no time limit
#   - This script is the ONLY thing Task Scheduler manages
#   - listener.py runs as a child, but decoupled via Start-Process
#   - PID lock file prevents multiple watchdog instances

param(
    [int]$CheckIntervalSeconds = 60,
    [int]$LivenessStaleSeconds = 120,
    [int]$MaxConsecutiveFailures = 3,
    [int]$MaxBackoffSeconds = 300,
    [int]$MaxLogSizeKB = 1024,
    [int]$ClaudeCodeTimeoutMinutes = 15
)

$ErrorActionPreference = "Stop"

# -- Paths --
$ScriptDir    = Split-Path -Parent $MyInvocation.MyCommand.Definition
if (-not $ScriptDir) { $ScriptDir = "$PWD" }
$WorkDir      = $ScriptDir
$PythonExe    = Join-Path $WorkDir "venv\Scripts\python.exe"
$ListenerPy   = Join-Path $WorkDir "listener.py"
$LivenessFile = Join-Path $WorkDir "liveness.txt"
$LogFile      = Join-Path $WorkDir "comet-watchdog.log"
$LockFile     = Join-Path $WorkDir "comet-watchdog.pid"
$StateFile    = Join-Path $WorkDir "comet-watchdog-state.json"
$TaskName     = "CometListener-Watchdog"

# -- Escalation config --
$TelegramBotToken = $null
$TelegramChatId   = "-1003918620814"

# -- Logging --
function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp [$Level] $Message" | Out-File -Append -FilePath $LogFile -Encoding UTF8
}

function Rotate-Log {
    if ((Test-Path $LogFile) -and ((Get-Item $LogFile).Length / 1KB) -gt $MaxLogSizeKB) {
        $backup = Join-Path $ScriptDir "comet-watchdog-prev.log"
        if (Test-Path $backup) { Remove-Item $backup -Force }
        Move-Item $LogFile $backup -Force
        Write-Log "Log rotated"
    }
}

# -- PID Lock --
function Acquire-Lock {
    if (Test-Path $LockFile) {
        $oldPid = Get-Content $LockFile -ErrorAction SilentlyContinue
        if ($oldPid -and ($oldPid -ne $PID.ToString())) {
            $oldProc = Get-Process -Id $oldPid -ErrorAction SilentlyContinue
            if ($oldProc -and $oldProc.ProcessName -match "powershell") {
                Write-Log "Another watchdog instance running (PID $oldPid), exiting" "WARN"
                exit 0
            }
            Write-Log "Stale lock file (PID $oldPid not running), taking over" "WARN"
        }
    }
    $PID.ToString() | Out-File $LockFile -Encoding UTF8 -Force
}

function Release-Lock {
    if (Test-Path $LockFile) {
        $currentOwner = Get-Content $LockFile -ErrorAction SilentlyContinue
        if ($currentOwner -eq $PID.ToString()) {
            Remove-Item $LockFile -Force -ErrorAction SilentlyContinue
        }
    }
}

# -- State management --
function Get-State {
    if (Test-Path $StateFile) {
        try {
            return Get-Content $StateFile -Raw | ConvertFrom-Json
        } catch {
            return @{ consecutiveFailures = 0; lastFailureTime = $null; claudeAttempted = $false; telegramAlerted = $false }
        }
    }
    return @{ consecutiveFailures = 0; lastFailureTime = $null; claudeAttempted = $false; telegramAlerted = $false }
}

function Save-State {
    param([hashtable]$State)
    $State | ConvertTo-Json -Depth 3 | Out-File $StateFile -Encoding UTF8 -Force
}

# -- Load bot token from .env.local --
function Load-BotToken {
    $envFile = Join-Path (Split-Path $ScriptDir -Parent) ".env.local"
    if (Test-Path $envFile) {
        $content = Get-Content $envFile -ErrorAction SilentlyContinue
        foreach ($line in $content) {
            if ($line -match "^TELEGRAM_BOT_TOKEN=(.+)$") {
                $script:TelegramBotToken = $Matches[1].Trim()
                Write-Log "Loaded bot token from .env.local"
                return
            }
        }
    }
    Write-Log "Could not load TELEGRAM_BOT_TOKEN" "WARN"
}

# -- Health check --
function Test-ListenerAlive {
    # Check 1: Is the liveness file recent?
    if (Test-Path $LivenessFile) {
        $lastWrite = (Get-Item $LivenessFile).LastWriteTime
        $age = (Get-Date) - $lastWrite
        if ($age.TotalSeconds -lt $LivenessStaleSeconds) {
            return $true
        }
        Write-Log "Liveness file stale ($([math]::Round($age.TotalSeconds))s old)" "WARN"
    } else {
        Write-Log "Liveness file missing" "WARN"
    }

    # Check 2: Is there a python process running listener.py?
    $listenerProc = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
        $_.Path -like "*auto-pickup*"
    }
    if ($listenerProc) {
        Write-Log "Python process found (PID $($listenerProc.Id)) but liveness stale - probably hung" "WARN"
        try {
            Stop-Process -Id $listenerProc.Id -Force
            Write-Log "Killed hung listener PID $($listenerProc.Id)" "WARN"
        } catch {
            Write-Log "Failed to kill hung listener: $_" "ERROR"
        }
    }

    return $false
}

# -- Start listener --
function Start-Listener {
    Write-Log "Starting listener.py ..."
    try {
        $proc = Start-Process -FilePath $PythonExe `
            -ArgumentList "-B", "`"$ListenerPy`"", "-NoConsole" `
            -WorkingDirectory $WorkDir `
            -PassThru `
            -WindowStyle Hidden
        Write-Log "listener.py launched as PID $($proc.Id)"

        # Wait a bit and check it didn't immediately crash
        Start-Sleep -Seconds 10
        $check = Get-Process -Id $proc.Id -ErrorAction SilentlyContinue
        if ($check) {
            Write-Log "Listener PID $($proc.Id) confirmed running after 10s"
            return $true
        } else {
            Write-Log "Listener PID $($proc.Id) died within 10 seconds" "ERROR"
            return $false
        }
    } catch {
        Write-Log "Failed to start listener: $_" "ERROR"
        return $false
    }
}

# -- Escalation: Claude Code --
function Invoke-ClaudeCodeFix {
    param([hashtable]$State)

    if ($State.claudeAttempted) {
        Write-Log "Claude Code already attempted, skipping" "WARN"
        return $false
    }

    Write-Log "=== ESCALATION: Launching Claude Code to debug listener ===" "WARN"

    $logTail = ""
    $mainLog = Join-Path $WorkDir "telegram-watcher.log"
    if (Test-Path $mainLog) {
        $logTail = Get-Content $mainLog -Tail 50 -ErrorAction SilentlyContinue | Out-String
    }
    $stderrContent = ""
    $stderrPath = Join-Path $WorkDir "stderr.log"
    if (Test-Path $stderrPath) {
        $stderrContent = Get-Content $stderrPath -Tail 30 -ErrorAction SilentlyContinue | Out-String
    }

    $prompt = "The COMET listener at $WorkDir\listener.py has failed to start $MaxConsecutiveFailures times in a row. Recent log tail: $logTail. Recent stderr: $stderrContent. Your task: 1) Read listener.py and pyautomation.py 2) Identify why the listener is crashing or hanging 3) Fix the issue 4) Verify the fix by attempting to start the listener. Do NOT modify the watchdog script. Fix only the listener or its dependencies."

    try {
        $claudeProc = Start-Process -FilePath "wsl.exe" `
            -ArgumentList "-d", "Ubuntu", "--", "claude", "--dangerously-skip-permissions", "-p", $prompt `
            -PassThru `
            -WindowStyle Hidden

        $waited = 0
        $timeoutSec = $ClaudeCodeTimeoutMinutes * 60
        while ($waited -lt $timeoutSec) {
            Start-Sleep -Seconds 10
            $waited += 10
            if ($claudeProc.HasExited) { break }
        }

        if (-not $claudeProc.HasExited) {
            Write-Log "Claude Code timed out after $ClaudeCodeTimeoutMinutes minutes, killing" "ERROR"
            Stop-Process -Id $claudeProc.Id -Force -ErrorAction SilentlyContinue
            return $false
        }

        $exitCode = $claudeProc.ExitCode
        Write-Log "Claude Code exited with code $exitCode"
        return ($exitCode -eq 0)
    } catch {
        Write-Log "Failed to launch Claude Code: $_" "ERROR"
        return $false
    }
}

# -- Escalation: Telegram alert --
function Send-TelegramAlert {
    param([string]$Message)

    if (-not $TelegramBotToken) {
        Write-Log "Cannot send Telegram alert: no bot token" "ERROR"
        return $false
    }

    if ($script:telegramAlertSent) {
        Write-Log "Telegram alert already sent, skipping duplicate" "WARN"
        return $true
    }

    $uri = "https://api.telegram.org/bot${TelegramBotToken}/sendMessage"
    $body = @{
        chat_id = $TelegramChatId
        text    = $Message
    } | ConvertTo-Json -Depth 3

    try {
        Invoke-RestMethod -Uri $uri -Method Post -Body $body -ContentType "application/json" -TimeoutSec 30 | Out-Null
        Write-Log "Telegram alert sent successfully"
        $script:telegramAlertSent = $true
        return $true
    } catch {
        Write-Log "Failed to send Telegram alert: $_" "ERROR"
        return $false
    }
}

# -- Register self as scheduled task --
function Register-Watchdog {
    $action = New-ScheduledTaskAction -Execute "wscript.exe" -Argument """$ScriptDir\comet-watchdog.vbs""" -WorkingDirectory $ScriptDir
    $trigger = New-ScheduledTaskTrigger -AtLogOn
    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -RestartCount 99 `
        -RestartInterval (New-TimeSpan -Minutes 1) `
        -ExecutionTimeLimit ([TimeSpan]::Zero) `
        -MultipleInstances IgnoreNew

    $existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($existing) {
        Set-ScheduledTask -TaskName $TaskName -Action $action -Settings $settings | Out-Null
        Write-Log "Watchdog task updated"
    } else {
        Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description "COMET listener watchdog" -Force | Out-Null
        Write-Log "Watchdog task registered"
    }
}

# ================================================================
# MAIN
# ================================================================

trap {
    Write-Log "UNHANDLED: $_" "ERROR"
    Release-Lock
    break
}

Rotate-Log
Acquire-Lock
# Note: do NOT call Register-Watchdog here - it fails when run from
# inside the scheduled task (access denied). Registration is done
# by deploy-comet-watchdog.ps1 instead.
Load-BotToken

Write-Log "=== COMET Watchdog started (PID: $PID, interval: ${CheckIntervalSeconds}s) ==="
Write-Log "Liveness stale threshold: ${LivenessStaleSeconds}s"
Write-Log "Max consecutive failures before escalation: $MaxConsecutiveFailures"

$script:telegramAlertSent = $false

try {
    while ($true) {
        Rotate-Log

        $alive = Test-ListenerAlive

        if ($alive) {
            $state = Get-State
            if ($state.consecutiveFailures -gt 0) {
                Write-Log "Listener recovered after $($state.consecutiveFailures) failures - resetting state"
                Save-State @{ consecutiveFailures = 0; lastFailureTime = $null; claudeAttempted = $false; telegramAlerted = $false }
            }
            Start-Sleep -Seconds $CheckIntervalSeconds
            continue
        }

        # Listener is dead
        $state = Get-State
        $failures = [int]$state.consecutiveFailures + 1
        Write-Log "Listener dead - failure count: $failures / $MaxConsecutiveFailures" "WARN"

        if ($failures -le $MaxConsecutiveFailures) {
            # Try to restart
            $started = Start-Listener
            if ($started) {
                Write-Log "Listener restarted successfully (attempt $failures)"
                Save-State @{ consecutiveFailures = $failures; lastFailureTime = (Get-Date).ToString("o"); claudeAttempted = $false; telegramAlerted = $false }
                Start-Sleep -Seconds $CheckIntervalSeconds
                continue
            } else {
                Write-Log "Listener restart failed (attempt $failures)" "ERROR"
                Save-State @{ consecutiveFailures = $failures; lastFailureTime = (Get-Date).ToString("o"); claudeAttempted = $false; telegramAlerted = $false }
                $backoff = [Math]::Min(30 * [Math]::Pow(2, $failures - 1), $MaxBackoffSeconds)
                Write-Log "Backing off ${backoff}s before next attempt"
                Start-Sleep -Seconds $backoff
                continue
            }
        }

        # Past max failures - escalate
        Write-Log "=== FAILURE THRESHOLD REACHED ($failures consecutive failures) ===" "ERROR"

        # Escalation 1: Claude Code
        if (-not $state.claudeAttempted) {
            $claudeOk = Invoke-ClaudeCodeFix $state
            Save-State @{ consecutiveFailures = $failures; lastFailureTime = (Get-Date).ToString("o"); claudeAttempted = $true; telegramAlerted = $false }

            if ($claudeOk) {
                Write-Log "Claude Code reported success - resetting failure count"
                Save-State @{ consecutiveFailures = 0; lastFailureTime = $null; claudeAttempted = $false; telegramAlerted = $false }
                Start-Sleep -Seconds $CheckIntervalSeconds
                continue
            }
        }

        # Escalation 2: Telegram alert to Teneen
        if (-not $state.telegramAlerted) {
            $alertMsg = "COMET LISTENER DOWN. Failed $failures times, could not auto-recover. Claude Code escalation: $(if ($state.claudeAttempted) { 'ATTEMPTED AND FAILED' } else { 'SKIPPED' }). Log: $WorkDir\telegram-watcher.log. Teneen: Please notify Safwat/Ahmed M that COMET auto-pickup is offline."
            $sent = Send-TelegramAlert $alertMsg
            Save-State @{ consecutiveFailures = $failures; lastFailureTime = (Get-Date).ToString("o"); claudeAttempted = $true; telegramAlerted = $sent }
        }

        # Keep checking but at reduced frequency to avoid log spam
        Start-Sleep -Seconds 300
    }
}
finally {
    Write-Log "COMET Watchdog stopping" "WARN"
    Release-Lock
}
