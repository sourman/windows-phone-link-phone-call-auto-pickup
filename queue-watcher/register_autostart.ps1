# Register queue-watcher to auto-start at login via Task Scheduler.
# Run once as admin:  powershell -File register_autostart.ps1
#
# The task runs pythonw (no console window) and restarts on failure.

$ErrorActionPreference = "Stop"

$taskName = "QueueWatcher-AutoPickup"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$watcherPy = Join-Path $scriptDir "watcher.py"

# Use the venv's pythonw (no console window, has dependencies installed)
$pythonw = Join-Path $scriptDir "venv\Scripts\pythonw.exe"
if (-not (Test-Path $pythonw)) {
    Write-Error "venv pythonw not found at $pythonw. Run:  python -m venv venv;  venv\Scripts\pip install -r requirements.txt"
    exit 1
}

# Remove existing task if present
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

$action = New-ScheduledTaskAction -Execute $pythonw -Argument "`"$watcherPy`" -NoConsole" -WorkingDirectory $scriptDir
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Auto-pickup queue watcher - polls Cloudflare Queue for COMET SMS" `
    | Out-Null

Write-Host "Registered scheduled task '$taskName' for user $env:USERNAME"
Write-Host "  Executable : $pythonw"
Write-Host "  Script     : $watcherPy"
Write-Host ""
Write-Host "To start now  : schtasks /Run /TN `"$taskName`""
Write-Host "To stop       : schtasks /End /TN `"$taskName`""
$unreg = 'Unregister-ScheduledTask -TaskName "' + $taskName + '"'
Write-Host "To unregister : $unreg"
