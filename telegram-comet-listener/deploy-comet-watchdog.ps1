# deploy-comet-watchdog.ps1 - One-time setup for the COMET listener watchdog.
#
# What it does:
#   1. Kills any existing listener processes
#   2. Removes the OLD scheduled tasks
#   3. Registers the NEW watchdog-only task (Task Scheduler -> comet-watchdog.ps1)
#   4. Starts it immediately
#
# Run: powershell -ExecutionPolicy Bypass -File deploy-comet-watchdog.ps1

$ErrorActionPreference = "Stop"

$ScriptDir    = Split-Path -Parent $MyInvocation.MyCommand.Definition
$TaskName     = "CometListener-Watchdog"
$OldTaskNames = @("TelegramWatcher-AutoPickup")

Write-Host "=== COMET Watchdog Deployment ===" -ForegroundColor Cyan

# Step 1: Kill existing listener processes
Write-Host ""
Write-Host ">> Step 1: Killing existing listener processes..." -ForegroundColor Yellow
Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "*auto-pickup*" } | ForEach-Object {
    Write-Host "   Killing PID $($_.Id)..."
    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 2

# Step 2: Remove old scheduled tasks
Write-Host ""
Write-Host ">> Step 2: Removing old scheduled tasks..." -ForegroundColor Yellow
foreach ($old in $OldTaskNames) {
    $task = Get-ScheduledTask -TaskName $old -ErrorAction SilentlyContinue
    if ($task) {
        Write-Host "   Removing old task: $old"
        Stop-ScheduledTask -TaskName $old -ErrorAction SilentlyContinue
        Unregister-ScheduledTask -TaskName $old -Confirm:$false -ErrorAction SilentlyContinue
    } else {
        Write-Host "   Old task '$old' not found (already clean)"
    }
}

# Step 3: Register new watchdog task
Write-Host ""
Write-Host ">> Step 3: Registering new watchdog task..." -ForegroundColor Yellow

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

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

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "COMET listener watchdog - monitors liveness, restarts listener, escalates on repeated failures" `
    -Force | Out-Null

Write-Host "   Task '$TaskName' registered." -ForegroundColor Green

# Step 4: Start it now
Write-Host ""
Write-Host ">> Step 4: Starting watchdog..." -ForegroundColor Yellow
Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 5

$taskInfo = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($taskInfo) {
    Write-Host "   Task state: $($taskInfo.State)" -ForegroundColor Green
} else {
    Write-Host "   WARNING: Could not query task state" -ForegroundColor Red
}

# Step 5: Verify
Write-Host ""
Write-Host ">> Step 5: Verifying..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

$watchdogLog = Join-Path $ScriptDir "comet-watchdog.log"
if (Test-Path $watchdogLog) {
    $lastLines = Get-Content $watchdogLog -Tail 5
    Write-Host "   Watchdog log (last 5 lines):" -ForegroundColor Cyan
    $lastLines | ForEach-Object { Write-Host "     $_" }
} else {
    Write-Host "   WARNING: No watchdog log found yet" -ForegroundColor Red
}

$listenerProc = Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "*auto-pickup*" }

if ($listenerProc) {
    Write-Host ""
    Write-Host "   SUCCESS: Listener running as PID $($listenerProc.Id)" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "   Listener not yet running - watchdog may still be starting it. Check logs." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Deployment complete ===" -ForegroundColor Cyan
Write-Host "Watchdog task: $TaskName"
Write-Host "Watchdog log:  $watchdogLog"
Write-Host "State file:    $(Join-Path $ScriptDir 'comet-watchdog-state.json')"
Write-Host ""
Write-Host "Manual commands:" -ForegroundColor Cyan
Write-Host "  Start:  schtasks /Run /TN `"$TaskName`""
Write-Host "  Stop:   schtasks /End /TN `"$TaskName`""
Write-Host "  Remove: Unregister-ScheduledTask -TaskName '$TaskName'"
