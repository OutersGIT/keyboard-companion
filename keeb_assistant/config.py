"""Persistent JSON configuration stored in %APPDATA%/KeyboardCompanion."""

from __future__ import annotations

import json
import os
from pathlib import Path

from . import APP_ID

DEFAULTS = {
    "language": "en",
    "smoothing_alpha": 0.3,
    "smoothing_deadband": 1.5,
    "low_battery_threshold": 15,
    "notify_low_battery": True,
    "pull_interval_sec": 5.0,
    # Opt-in diagnostics: append battery samples to a CSV in %APPDATA%. Off by
    # default; used to gather real voltage/charging data for the charging-%
    # correction. Does not affect anything displayed.
    "battery_logging": False,
    # While charging, compensate the inflated terminal voltage so the shown %
    # tracks the true resting state of charge. offset_mv is the voltage we
    # subtract before mapping to % (empirical; refine from logged CSV data).
    "charge_correction": True,
    "charge_offset_mv": 120,
    # User preference for autostart; registry is synced on startup via
    # autostart.sync_from_config(). The menu checkbox reads the registry live.
    "autostart": False,
}


def config_dir() -> Path:
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    path = Path(base) / APP_ID
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_path() -> Path:
    return config_dir() / "config.json"


class Config:
    def __init__(self, data: dict | None = None):
        self._data = dict(DEFAULTS)
        if data:
            self._data.update({k: v for k, v in data.items() if k in DEFAULTS})

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value

    def get(self, key, default=None):
        return self._data.get(key, default)

    def as_dict(self) -> dict:
        return dict(self._data)

    @classmethod
    def load(cls) -> "Config":
        try:
            with open(config_path(), "r", encoding="utf-8") as fh:
                return cls(json.load(fh))
        except (OSError, ValueError):
            return cls()

    def save(self) -> None:
        try:
            with open(config_path(), "w", encoding="utf-8") as fh:
                json.dump(self._data, fh, indent=2)
        except OSError:
            pass
