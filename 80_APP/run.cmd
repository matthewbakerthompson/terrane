@echo off
rem Starts the local architecture model app, for a Windows machine whose
rem policy blocks PowerShell scripts: cmd runs this, and so does a double-click.
python "%~dp0app\server.py" %*
rem A double-clicked window closes the moment Python exits, taking the reason
rem with it; hold it open when the start failed.
if errorlevel 1 pause
