"""Bluetooth battery via Windows (mirror of what the OS already knows).

When the keyboard is connected over Bluetooth LE, its vendor raw-HID interface
is NOT exposed (only standard HID + the BLE Battery Service). Rather than
opening our own GATT connection (which can clash with the OS holding the HID
link), we simply read the battery level Windows already cached as a device
property: DEVPKEY_Bluetooth_Battery = {104EA319-6EE2-4701-BD47-8DDBF425BBE5},2.

This is read via PowerShell's Get-PnpDeviceProperty, matching the keyboard by
friendly name. No extra Python dependency required.
"""

from __future__ import annotations

import re
import subprocess
import sys

# Devices whose friendly name matches this are considered "our" keyboard(s).
NAME_PATTERN = "Keychron|K10|Lemokey"

_BATTERY_KEY = "{104EA319-6EE2-4701-BD47-8DDBF425BBE5} 2"

_PS_SCRIPT = (
    "$ErrorActionPreference='SilentlyContinue';"
    f"$key='{_BATTERY_KEY}';"
    f"Get-PnpDevice -PresentOnly | Where-Object {{ $_.FriendlyName -match '{NAME_PATTERN}' }} | "
    "ForEach-Object {"
    " $p = Get-PnpDeviceProperty -InstanceId $_.InstanceId -KeyName $key;"
    " if ($p -and $p.Data -ne $null) { Write-Output $p.Data }"
    "}"
)

_CREATE_NO_WINDOW = 0x08000000


def is_supported() -> bool:
    return sys.platform.startswith("win")


def read_bluetooth_battery() -> int | None:
    """Return the BLE battery percentage Windows reports, or None."""
    if not is_supported():
        return None
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", _PS_SCRIPT],
            capture_output=True,
            text=True,
            timeout=8,
            creationflags=_CREATE_NO_WINDOW,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    for token in re.findall(r"\d+", proc.stdout or ""):
        value = int(token)
        if 0 <= value <= 100:
            return value
    return None
