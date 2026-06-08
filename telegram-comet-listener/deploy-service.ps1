<#
  deploy-service.ps1 — One-time deployment: kill old task, register new task, start it.
  Run this elevated (right-click Run as Administrator) or from an elevated PowerShell.
#>
$ErrorActionPreference = "Stop"

$WorkDir = "C:\Users\ggg\projects\auto-pickup\telegram-comet-listener"
$WrapperScript = "$WorkDir\watchdog-wrapper.ps1"
$TaskName = "TelegramWatcher-AutoPickup"

Write-Host ">> Stopping any running listener processes..." -ForegroundColor Cyan
Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "*auto-pickup*" } | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

Write-Host ">> Removing old task if present..." -ForegroundColor Cyan
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

Write-Host ">> Creating new scheduled task..." -ForegroundColor Cyan
$argStr = "-ExecutionPolicy Bypass -WindowStyle Hidden -File `"$WrapperScript`""
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argStr -WorkingDirectory $WorkDir
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Minutes 2) `
    -MultipleInstances IgnoreNew

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Description "Long-polls Telegram for COMET triggers. Runs in user session for UIA." `
    -Force

Write-Host ">> Task registered. Verifying config..." -ForegroundColor Cyan
$task = Get-ScheduledTask -TaskName $TaskName
$task.Settings | Select-Object ExecutionTimeLimit, RestartCount, RestartInterval, MultipleInstances | Format-List

Write-Host ">> Starting task..." -ForegroundColor Cyan
Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 5

$info = Get-ScheduledTask -TaskName $TaskName
Write-Host "Task state: $($info.State)" -ForegroundColor $(if ($info.State -eq 'Running') { 'Green' } else { 'Yellow' })

$py = Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "*auto-pickup*" }
if ($py) {
    Write-Host "Python listener PID: $($py.Id) started at $($py.StartTime)" -ForegroundColor Green
} else {
    Write-Host "WARNING: No python listener process detected yet" -ForegroundColor Yellow
}
