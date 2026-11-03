@echo off
setlocal DisableDelayedExpansion
"%~dp0ModManager.exe" %*
if errorlevel 1 pause
