<#
  register-task-scheduler.ps1 -- One-time setup: configure the Telegram listener
  as a robust Task Scheduler task that runs in the user's interactive session.

  What it does:
    1. Removes the old task (if present) for clean reinstall.
    2. Creates a new task triggered at user logon AND at task creation/modification.
    3. Runs start-listener.bat (which calls watchdog-wrapper.ps1).
    4. Sets ExecutionTimeLimit to PT0S (unlimited -- no more 72-hour kills).
    5. Configures restart on failure (every 2 minutes, up to 999 times).
    6. Sets RunOnlyIfNetworkAvailable to false (network may not be ready at logon).
    7. Starts the task immediately.

  Run once from PowerShell (no admin needed since it's a user task):
    .\register-task-scheduler.ps1
#>

$ErrorActionPreference = "Stop"

# -- Paths --
$WorkDir       = "C:\Users\ggg\projects\auto-pickup\telegram-comet-listener"
$BatchLauncher = "$WorkDir\start-listener.bat"
$TaskName      = "TelegramWatcher-AutoPickup"

# -- Helper --
function Write-Step($msg) {
    Write-Host "`n>> $msg" -ForegroundColor Cyan
}

# -- 1. Remove existing task for clean reinstall --
Write-Step "Removing old task if present..."
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

# -- 2. Create the action (use the batch launcher for simplicity) --
Write-Step "Creating scheduled task..."
$action = New-ScheduledTaskAction `
    -Execute "cmd.exe" `
    -Argument "/c `"$BatchLauncher`"" `
    -WorkingDirectory $WorkDir

# -- 3. Create trigger: logon (task starts immediately via Start-ScheduledTask below) --
$triggerLogon = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

# -- 4. Configure settings --
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Days 0) `
    -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Minutes 2) `
    -MultipleInstances IgnoreNew

# Disable RunOnlyIfNetworkAvailable -- network may not be ready at logon
$settings.RunOnlyIfNetworkAvailable = $false

# -- 5. Register the task --
Write-Step "Registering task..."
Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $triggerLogon `
    -Settings $settings `
    -Description "Long-polls Telegram for COMET triggers and runs pyautomation comet+call sequence. Runs in user session for UIA desktop access." `
    -Force

Write-Host "Task registered with ExecutionTimeLimit=unlimited, RestartCount=999, RestartInterval=2min, RunOnlyIfNetworkAvailable=false" -ForegroundColor Green

# -- 6. Verify the execution time limit and settings --
Write-Step "Verifying task configuration..."
$task = Get-ScheduledTask -TaskName $TaskName
$task.Settings | Select-Object ExecutionTimeLimit, RestartCount, RestartInterval, MultipleInstances, RunOnlyIfNetworkAvailable | Format-List

# Double-check ExecutionTimeLimit is actually PT0S
$etl = $task.Settings.ExecutionTimeLimit
if ($etl -ne "PT0S" -and $etl -ne "9999:59:59:59" -and $etl -ne "99999:59:59:59") {
    Write-Warning "ExecutionTimeLimit is '$etl' -- expected PT0S (unlimited). Attempting to force it..."
    $task.Settings.ExecutionTimeLimit = "PT0S"
    Set-ScheduledTask -InputObject $task
    Write-Host "Force-set ExecutionTimeLimit to PT0S" -ForegroundColor Yellow
}

# -- 7. Start the task now --
Write-Step "Starting task..."
Start-ScheduledTask -TaskName $TaskName

Start-Sleep -Seconds 3
$taskInfo = Get-ScheduledTask -TaskName $TaskName
if ($taskInfo.State -eq 'Running') {
    Write-Host "`nTask '$TaskName' is RUNNING." -ForegroundColor Green
} else {
    Write-Warning "Task '$TaskName' state: $($taskInfo.State). Check logs at $WorkDir\watchdog-wrapper.log and $WorkDir\telegram-watcher.log"
}

Write-Host "`nDone. Task runs at logon and starts immediately via Start-ScheduledTask above."
