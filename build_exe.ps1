$ErrorActionPreference = "Stop"

Write-Host "Building CAN ASC Recorder executable..."

python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name CAN_ASC_Recorder `
    --collect-submodules can.interfaces `
    --hidden-import serial.tools.list_ports_windows `
    can_recorder_gui.py

Write-Host ""
Write-Host "Build complete: dist\CAN_ASC_Recorder.exe"
