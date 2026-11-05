@echo off
if not exist "%~dp0.venv\Scripts\pythonw.exe" (
    echo Run setup first: powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 -WithEditor
    pause
    exit /b 1
)
start "" /D "%~dp0" "%~dp0.venv\Scripts\pythonw.exe" "%~dp0launch_editor.pyw"
