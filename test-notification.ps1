# Test Notification - Simulates a Phone Link SMS notification
# This creates a balloon notification similar to what Phone Link shows

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# Create the NotifyIcon
$balloon = New-Object System.Windows.Forms.NotifyIcon
$balloon.Icon = [System.Drawing.SystemIcons]::Information
$balloon.Visible = $true

# Set the balloon tip properties
$balloon.BalloonTipIcon = [System.Windows.Forms.ToolTipIcon]::Info
$balloon.BalloonTipTitle = "+16463612549"
$balloon.BalloonTipText = "TENEEN`nvia Phone Link"

# Show the notification for 6 seconds
$balloon.ShowBalloonTip(6000)

# Cleanup
$balloon.Dispose()
