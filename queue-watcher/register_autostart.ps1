# Register queue-watcher to auto-start at login via Task Scheduler.
# Run once as admin:  powershell -File register_autostart.ps1
#
# The task runs pythonw (no console window) and restarts on failure.

$ErrorActionPreference = "Stop"

$taskName = "QueueWatcher-AutoPickup"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$watcherPy = Join-Path $scriptDir "watcher.py"

# Find pythonw (no console window)
$pythonw = Get-Command pythonw -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
if (-not $pythonw) {
    $pythonw = Get-Command python -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
    if (-not $pythonw) {
        Write-Error "python/pythonw not found on PATH"
        exit 1
    }
    Write-Warning "pythonw not found, using python (will show a console window)"
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
    -Description "Auto-pickup queue watcher — polls Cloudflare Queue for COMET SMS" `
    | Out-Null

Write-Host "Registered scheduled task '$taskName' for user $env:USERNAME"
Write-Host "  Executable : $pythonw"
Write-Host "  Script     : $watcherPy"
Write-Host ""
Write-Host "To start now  : schtasks /Run /TN `"$taskName`""
Write-Host "To stop       : schtasks /End /TN `"$taskName`""
Write-Host "To unregister : Unregister-ScheduledTask -TaskName `"$taskName`""
