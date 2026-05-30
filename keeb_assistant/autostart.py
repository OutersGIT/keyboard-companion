"""Optional Windows auto-start via the per-user Run registry key.

The user controls this from the tray menu; nothing is enabled by default.
Works both when running as a frozen .exe and as a `python -m` script.
"""

from __future__ import annotations

import sys
from pathlib import Path

from . import APP_ID

_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _is_windows() -> bool:
    return sys.platform.startswith("win")


def _launch_command() -> str:
    """Command Windows should run at logon."""
    if getattr(sys, "frozen", False):
        # Packaged single-exe: just run it.
        return f'"{sys.executable}"'
    # Dev mode: run with pythonw (no console window) -m keeb_assistant
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    runner = pythonw if pythonw.exists() else Path(sys.executable)
    return f'"{runner}" -m keeb_assistant'


def is_enabled() -> bool:
    if not _is_windows():
        return False
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as key:
            value, _ = winreg.QueryValueEx(key, APP_ID)
            return bool(value)
    except FileNotFoundError:
        return False
    except OSError:
        return False


def set_enabled(enabled: bool) -> bool:
    """Enable/disable autostart. Returns the resulting state."""
    if not _is_windows():
        return False
    import winreg

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            if enabled:
                winreg.SetValueEx(key, APP_ID, 0, winreg.REG_SZ, _launch_command())
            else:
                try:
                    winreg.DeleteValue(key, APP_ID)
                except FileNotFoundError:
                    pass
    except OSError:
        return is_enabled()
    return enabled
