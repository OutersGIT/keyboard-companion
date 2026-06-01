# Build Keyboard Companion as a PyInstaller onedir folder (+ optional zip).
#
# Usage (PowerShell, from this folder):
#   .\build_exe.ps1            # build dist\KeyboardCompanion\ + zip
#   .\build_exe.ps1 -Clean     # remove previous build artifacts first
#
param([switch]$Clean)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$AppDir = "dist\KeyboardCompanion"
$AppExe = "$AppDir\KeyboardCompanion.exe"
$ZipPath = "dist\KeyboardCompanion-win64.zip"

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

# onedir: a normal exe + bundled deps in the same folder (no temp self-extract).
# --noupx avoids UPX compression, which AV heuristics often flag.
# --collect-all bundles the hidapi DLL and the pystray win32 backend.
python -m PyInstaller --noconfirm --noconsole --onedir --noupx `
    --name KeyboardCompanion `
    --icon assets\app.ico `
    --version-file version_info.txt `
    --collect-all hid `
    --collect-all pystray `
    run_tray.py

if ($LASTEXITCODE -ne 0 -or -not (Test-Path $AppExe)) {
    Write-Error "Build failed (PyInstaller exit code $LASTEXITCODE)."
    exit 1
}

if (Test-Path $ZipPath) { Remove-Item -Force $ZipPath }
Compress-Archive -Path $AppDir -DestinationPath $ZipPath -Force

Write-Host ""
Write-Host "Done."
Write-Host "  Run:       $AppExe"
Write-Host "  Folder:    $AppDir  (keep all files together)"
Write-Host "  Zip:       $ZipPath  (for distribution)"
