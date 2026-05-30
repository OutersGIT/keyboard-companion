# Build a single-file Windows .exe for KC Utility Assistant.
#
# Usage (PowerShell, from this folder):
#   .\build_exe.ps1            # build
#   .\build_exe.ps1 -Clean     # remove previous build artifacts first
#
param([switch]$Clean)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if ($Clean) {
    Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
    Remove-Item -Force *.spec -ErrorAction SilentlyContinue
}

python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller

# Regenerate the app icon (battery glyph) if missing.
if (-not (Test-Path assets\app.ico)) { python make_app_icon.py }

# --collect-all bundles the hidapi DLL and the pystray win32 backend.
# --icon + --version-file give the exe its own identity (name/icon) so Windows
# shows "KC Utility Assistant" instead of "Python" in the tray/taskbar settings.
python -m PyInstaller --noconfirm --noconsole --onefile `
    --name KCUtilityAssistant `
    --icon assets\app.ico `
    --version-file version_info.txt `
    --collect-all hid `
    --collect-all pystray `
    run_tray.py

Write-Host ""
Write-Host "Done. Executable: dist\KCUtilityAssistant.exe"
