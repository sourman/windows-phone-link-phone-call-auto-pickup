$WorkDir = "C:\Users\ggg\projects\auto-pickup\telegram-comet-listener"
$WrapperScript = "$WorkDir\watchdog-wrapper.ps1"
$TaskName = "TelegramWatcher-AutoPickup"

Write-Host ">> Killing existing listener processes..."
Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "*auto-pickup*" } | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# Try Register-ScheduledTask - if fails, fall through to direct start
$registered = $false
try {
    $ErrorActionPreference = "Stop"
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    
    $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$WrapperScript`"" -WorkingDirectory $WorkDir
    $trigger = New-ScheduledTaskTrigger -AtLogOn
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 2) -MultipleInstances IgnoreNew
    
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description "Long-polls Telegram for COMET triggers." -Force
    $registered = $true
    Write-Host "Task registered."
} catch {
    Write-Host "Register-ScheduledTask failed: $($_.Exception.Message)"
    Write-Host "Will start listener directly as fallback."
}

if ($registered) {
    Write-Host ">> Starting scheduled task..."
    Start-ScheduledTask -TaskName $TaskName
    Start-Sleep -Seconds 5
    try {
        $info = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
        Write-Host "Task state: $($info.State)"
    } catch {
        Write-Host "Could not query task state"
    }
} else {
    Write-Host ">> Starting listener directly..."
    $proc = Start-Process -FilePath "$WorkDir\venv\Scripts\python.exe" -ArgumentList "-B","`"$WorkDir\listener.py`"","-NoConsole" -WorkingDirectory $WorkDir -PassThru -WindowStyle Hidden
    Start-Sleep -Seconds 5
    if ($proc -and -not $proc.HasExited) {
        Write-Host "Listener started as PID: $($proc.Id)"
    } elseif ($proc) {
        Write-Host "Listener exited with code: $($proc.ExitCode)"
    }
}

$py = Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "*auto-pickup*" }
if ($py) { Write-Host "SUCCESS: Python listener running PID: $($py.Id)" }
else { Write-Host "WARNING: No python listener process detected" }
