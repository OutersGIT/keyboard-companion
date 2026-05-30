"""System-tray application wiring reader + smoothing + icon + i18n + config."""

from __future__ import annotations

import sys
import threading
import time
import webbrowser

import pystray
from pystray import Menu, MenuItem

from . import APP_ID, APP_NAME, autostart, battery_log, battery_model, ble_reader, i18n
from .config import Config
from .hid_reader import BatteryReader, BatteryReading
from .icon import make_icon
from .smoothing import BatterySmoother

STALE_AFTER = 20.0       # seconds without data before the reading is "old"
UI_TICK = 2.0            # seconds between tooltip refreshes
BLE_POLL = 15.0          # seconds between Windows BLE battery polls (when no HID)
TRANSPORT_BLUETOOTH = 2
LAUNCHER_URL = "https://launcher.keychron.com/"


class TrayApp:
    def __init__(self):
        self.config = Config.load()
        i18n.set_language(self.config.get("language", i18n.DEFAULT_LANGUAGE))
        self.smoother = BatterySmoother(
            alpha=self.config["smoothing_alpha"],
            deadband=self.config["smoothing_deadband"],
        )

        self._lock = threading.Lock()
        self._latest: BatteryReading | None = None
        self._displayed_pct: int | None = None
        self._connected = False
        self._low_notified = False
        self._last_hid_ts = 0.0  # last time a cable/dongle raw-HID reading arrived
        self._stop = threading.Event()
        self._settings_open = threading.Event()

        self.icon = pystray.Icon(
            APP_ID,
            icon=make_icon(None, connected=False),
            title=f"{APP_NAME}\n• {i18n.t('tooltip_waiting')}",
            menu=self._build_menu(),
        )
        self.reader = BatteryReader(
            on_update=self._on_reading,
            on_status=self._on_status,
            pull_interval=float(self.config["pull_interval_sec"]),
        )

    # -- menu --------------------------------------------------------------
    def _language_menu(self) -> Menu:
        items = []
        for code, label in i18n.available_languages():
            items.append(
                MenuItem(
                    label,
                    self._make_lang_setter(code),
                    checked=self._make_lang_checker(code),
                    radio=True,
                )
            )
        return Menu(*items)

    def _make_lang_setter(self, code):
        def _set(icon, item):
            self.set_language(code)
        return _set

    def _make_lang_checker(self, code):
        return lambda item: i18n.get_language() == code

    def _build_menu(self) -> Menu:
        # Intentionally no live values here: all battery info lives in the
        # tooltip. A static menu means update_menu() is only called on explicit
        # user actions, so the hover highlight never gets rebuilt mid-hover.
        return Menu(
            MenuItem(lambda item: i18n.t("menu_settings"), self._open_settings),
            MenuItem(lambda item: i18n.t("menu_open_launcher"), self._open_launcher),
            MenuItem(lambda item: i18n.t("menu_language"), self._language_menu()),
            MenuItem(
                lambda item: i18n.t("menu_autostart"),
                self._toggle_autostart,
                checked=lambda item: autostart.is_enabled(),
            ),
            MenuItem(
                lambda item: i18n.t("menu_notify"),
                self._toggle_notify,
                checked=lambda item: bool(self.config["notify_low_battery"]),
            ),
            Menu.SEPARATOR,
            MenuItem(lambda item: i18n.t("menu_quit"), self._quit),
        )

    def _snapshot(self):
        """Return (reading, pct) only if data is present AND fresh, else (None, None).

        Stale data (no updates for STALE_AFTER, e.g. keyboard moved to a transport
        the app can't read like Bluetooth) is reported as 'Undetected', never as the
        last known value.
        """
        with self._lock:
            reading = self._latest
            pct = self._displayed_pct
            connected = self._connected
        if reading is None or not connected:
            return None, None
        if (time.time() - reading.timestamp) >= STALE_AFTER:
            return None, None
        return reading, pct

    def _tooltip_text(self) -> str:
        """Multi-line tray tooltip: app name + one bullet per field."""
        reading, pct = self._snapshot()
        if reading is None:
            return f"{APP_NAME}\n• {i18n.t('undetected')}"
        # Bullet layout, with the transport always in the same (last) slot:
        #   • <pct>%
        #   • <charging>   (only when known — not available over the BLE mirror)
        #   • <transport>  ("Bluetooth" / "2.4 GHz" / "USB")
        lines = [APP_NAME, f"• {pct}%"]
        if reading.source != "windows":
            lines.append(f"• {reading.voltage_mv} mV")
            lines.append(f"• {i18n.t(f'charging_{reading.charging_code}')}")
        lines.append(f"• {reading.transport_name}")
        return "\n".join(lines)

    # -- reader callbacks --------------------------------------------------
    def _on_status(self, connected: bool) -> None:
        with self._lock:
            self._connected = connected
            if not connected:
                self.smoother.reset()
                self._displayed_pct = None
        self._refresh_ui()

    def _on_reading(self, reading: BatteryReading) -> None:
        with self._lock:
            prev = self._latest
        # Switching source (HID cable/dongle <-> Windows BLE) can be a jump; start
        # the smoother fresh so we don't blend two different estimates.
        if prev is not None and prev.source != reading.source:
            self.smoother.reset()
        # Charging compensation is applied to the value we *display* only; the
        # raw voltage/percentage are still logged below as ground truth.
        corrected = battery_model.corrected_percentage(
            reading.voltage_mv,
            reading.percentage,
            reading.charging_code,
            enabled=bool(self.config.get("charge_correction", True)),
            offset_mv=int(self.config.get("charge_offset_mv", battery_model.DEFAULT_CHARGE_OFFSET_MV)),
        )
        displayed = self.smoother.update(corrected, charging=reading.is_charging)
        with self._lock:
            self._latest = reading
            self._displayed_pct = displayed
            self._connected = True
            if reading.source == "hid":
                self._last_hid_ts = reading.timestamp
        if self.config.get("battery_logging"):
            battery_log.append(
                source=reading.source,
                transport=reading.transport_name,
                charging=reading.charging_code,
                voltage_mv=reading.voltage_mv,
                raw_pct=reading.percentage,
                displayed_pct=displayed,
                ema=self.smoother.ema,
            )
        self._check_low_battery(displayed, reading.is_charging)
        self._refresh_ui()

    def _ble_poller(self) -> None:
        """When no cable/dongle HID data is flowing, mirror Windows' BLE battery."""
        if not ble_reader.is_supported():
            return
        # Small initial delay so HID (cable/dongle) gets first chance.
        if self._stop.wait(3.0):
            return
        while not self._stop.is_set():
            hid_active = (time.time() - self._last_hid_ts) < STALE_AFTER
            if not hid_active:
                pct = ble_reader.read_bluetooth_battery()
                if pct is not None:
                    self._on_reading(
                        BatteryReading(
                            percentage=pct,
                            voltage_mv=0,
                            charging=0,
                            transport=TRANSPORT_BLUETOOTH,
                            timestamp=time.time(),
                            source="windows",
                        )
                    )
            if self._stop.wait(BLE_POLL):
                break

    # -- ui ----------------------------------------------------------------
    def _refresh_ui(self) -> None:
        reading, pct = self._snapshot()
        if reading is None:
            # Stale/absent -> Undetected. Drop the smoother so a later reconnect
            # (possibly on another transport with a different level) starts clean.
            with self._lock:
                if self._displayed_pct is not None:
                    self.smoother.reset()
                    self._displayed_pct = None
            icon_img = make_icon(None, connected=False)
        else:
            icon_img = make_icon(pct, charging=reading.is_charging, connected=True)
        # Icon image + tooltip are cheap to set and don't disturb an open menu.
        # The menu carries no live values, so it is never rebuilt from here.
        try:
            self.icon.icon = icon_img
            self.icon.title = self._tooltip_text()
        except Exception:
            pass

    def _check_low_battery(self, pct: int | None, charging: bool) -> None:
        if pct is None or not self.config["notify_low_battery"]:
            return
        threshold = int(self.config["low_battery_threshold"])
        if charging or pct > threshold + 5:
            self._low_notified = False
            return
        if pct <= threshold and not self._low_notified:
            self._low_notified = True
            try:
                self.icon.notify(
                    i18n.t("notify_low_body", pct=pct),
                    i18n.t("notify_low_title"),
                )
            except Exception:
                pass

    def _ui_ticker(self) -> None:
        while not self._stop.wait(UI_TICK):
            self._refresh_ui()

    # -- settings integration ---------------------------------------------
    def set_language(self, code: str) -> None:
        i18n.set_language(code)
        self.config["language"] = i18n.get_language()
        self.config.save()
        self._refresh_ui()
        self._force_menu_update()  # relabel all menu items in the new language

    def apply_settings(self) -> None:
        """Re-read config values that affect runtime behavior (from the window)."""
        i18n.set_language(self.config.get("language", i18n.DEFAULT_LANGUAGE))
        self.smoother.alpha = max(0.01, min(1.0, float(self.config["smoothing_alpha"])))
        self.smoother.deadband = max(0.0, float(self.config["smoothing_deadband"]))
        self.config.save()
        self._refresh_ui()

    def _open_settings(self, icon=None, item=None) -> None:
        if self._settings_open.is_set():
            return

        def _run():
            self._settings_open.set()
            try:
                from .settings_window import open_settings
                open_settings(self)
            except Exception:
                pass
            finally:
                self._settings_open.clear()

        threading.Thread(target=_run, daemon=True, name="SettingsWindow").start()

    # -- menu actions ------------------------------------------------------
    def _toggle_autostart(self, icon, item) -> None:
        result = autostart.set_enabled(not autostart.is_enabled())
        self.config["autostart"] = result
        self.config.save()
        self._force_menu_update()

    def _toggle_notify(self, icon, item) -> None:
        self.config["notify_low_battery"] = not self.config["notify_low_battery"]
        self.config.save()
        self._force_menu_update()

    def _force_menu_update(self) -> None:
        """Rebuild the menu now (used after a click closes it, so no hover issue)."""
        try:
            self.icon.update_menu()
        except Exception:
            pass

    def _open_launcher(self, icon=None, item=None) -> None:
        try:
            webbrowser.open(LAUNCHER_URL)
        except Exception:
            pass

    def _quit(self, icon, item) -> None:
        self._stop.set()
        self.reader.stop()
        icon.stop()

    # -- lifecycle ---------------------------------------------------------
    def _install_doubleclick_handler(self) -> None:
        """Open Settings on a tray double-click.

        pystray's cross-platform API only exposes a single 'default' action, but
        on Windows the shell still delivers WM_LBUTTONDBLCLK to the icon's
        callback. We hook the win32 backend's notify dispatch to catch it and
        leave single-click unbound. No-op (and harmless) on other platforms or
        if pystray internals ever change.
        """
        if not sys.platform.startswith("win"):
            return
        try:
            from pystray._util import win32 as _w32

            WM_LBUTTONDBLCLK = 0x0203
            base = self.icon._on_notify

            def _on_notify(wparam, lparam):
                if lparam == WM_LBUTTONDBLCLK:
                    self._open_settings()
                    return None
                return base(wparam, lparam)

            self.icon._message_handlers[_w32.WM_NOTIFY] = _on_notify
        except Exception:
            pass

    def _setup(self, icon) -> None:
        icon.visible = True
        self._install_doubleclick_handler()
        self.reader.start()
        threading.Thread(target=self._ui_ticker, daemon=True, name="UiTicker").start()
        threading.Thread(target=self._ble_poller, daemon=True, name="BlePoller").start()

    def run(self) -> None:
        self.icon.run(setup=self._setup)


def _set_app_user_model_id() -> None:
    """Give the process a stable identity so Windows tracks the tray icon
    consistently (name + the 'always show' setting)."""
    if not sys.platform.startswith("win"):
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            f"{APP_ID}.Tray"
        )
    except Exception:
        pass


def main() -> None:
    _set_app_user_model_id()
    TrayApp().run()


if __name__ == "__main__":
    main()
