# Build a single-file Windows .exe for Keyboard Companion.
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

# Python 3.14's experimental JIT crashes PyInstaller's module analysis
# (Fatal Python error in dis._deoptop). Disabling it makes the build reliable.
$env:PYTHON_JIT = "0"

# Regenerate the app icon (battery glyph) if missing.
if (-not (Test-Path assets\app.ico)) { python make_app_icon.py }

# PyInstaller prints its INFO log to stderr. With $ErrorActionPreference="Stop"
# (and PS 7.4+ defaults) PowerShell would treat that as a fatal error and abort,
# so relax it for the native build and check the exit code ourselves instead.
$ErrorActionPreference = "Continue"

# --collect-all bundles the hidapi DLL and the pystray win32 backend.
# --icon + --version-file give the exe its own identity (name/icon) so Windows
# shows "Keyboard Companion" instead of "Python" in the tray/taskbar settings.
python -m PyInstaller --noconfirm --noconsole --onefile `
    --name KeyboardCompanion `
    --icon assets\app.ico `
    --version-file version_info.txt `
    --collect-all hid `
    --collect-all pystray `
    run_tray.py

if ($LASTEXITCODE -ne 0 -or -not (Test-Path dist\KeyboardCompanion.exe)) {
    Write-Error "Build failed (PyInstaller exit code $LASTEXITCODE)."
    exit 1
}

Write-Host ""
Write-Host "Done. Executable: dist\KeyboardCompanion.exe"
