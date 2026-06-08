@echo off
REM start-listener.bat — Launcher for the Telegram COMET listener watchdog
REM Called by Windows Task Scheduler
REM Runs the PowerShell watchdog wrapper which manages listener.py lifecycle

cd /d "C:\Users\ggg\projects\auto-pickup\telegram-comet-listener"
powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0watchdog-wrapper.ps1"
