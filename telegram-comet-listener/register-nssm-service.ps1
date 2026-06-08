<#
  register-nssm-service.ps1 — NOTE: NSSM approach was rejected by review.

  NSSM services run in Session 0 (no interactive desktop). This service needs
  UIA / pyautogui which requires an active user desktop. DO NOT USE NSSM.

  This file is kept for reference only. The correct setup is Task Scheduler.
  See register-task-scheduler.ps1 for the working approach.
#>
Write-Warning "NSSM approach does NOT work for this service — UIA requires interactive desktop. Use register-task-scheduler.ps1 instead."
