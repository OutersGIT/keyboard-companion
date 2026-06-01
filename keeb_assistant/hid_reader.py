"""HID communication layer.

Unifies the two ways of getting the battery state from the keyboard:

* PUSH (2.4 GHz dongle): the keyboard sends an unsolicited raw-HID report
  (command 0xA4) every couple of seconds. We just read it.
* PULL (USB cable): we send the 0xA4 command and read the reply.

The reader opens every Keychron raw-HID interface it finds (VID 0x3434,
usage page 0xFF60), reads passively, and also issues an occasional pull so the
cable case works too. Devices appearing/disappearing (mode switch, dongle
unplug) are handled by periodic re-enumeration.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass

try:
    import hid  # type: ignore
except ImportError:  # pragma: no cover - import guard for friendlier error
    hid = None

VENDOR_ID = 0x3434          # Keychron
RAW_USAGE_PAGE = 0xFF60     # QMK raw HID
RAW_USAGE = 0x61
REPORT_SIZE = 32
KC_GET_BATTERY = 0xA4
KC_GET_FIRMWARE_VERSION = 0xA1

# Language-neutral transport labels (brand/standard names, not translated).
TRANSPORT_NAMES = {1: "USB", 2: "Bluetooth", 4: "2.4 GHz"}


@dataclass(frozen=True)
class BatteryReading:
    percentage: int
    voltage_mv: int
    charging: int
    transport: int
    timestamp: float
    source: str = "hid"  # "hid" (cable/dongle raw HID) or "windows" (BLE mirror)
     # Optional model identifier from KC_GET_BATTERY (0 = unspecified/legacy).
    model_id: int = 0

    @property
    def transport_name(self) -> str:
        return TRANSPORT_NAMES.get(self.transport, f"? ({self.transport})")

    @property
    def charging_code(self) -> int:
        # 0 = on battery, 1 = charging, 2 = full. UI maps this to a localized string.
        return self.charging if self.charging in (0, 1, 2) else 0

    @property
    def is_charging(self) -> bool:
        return self.charging in (1, 2)


def _parse_report(resp) -> BatteryReading | None:
    """Decode a raw-HID buffer into a BatteryReading, or None if not ours."""
    if not resp:
        return None
    # Some platforms prepend the report id (0x00); tolerate a leading byte.
    if resp[0] != KC_GET_BATTERY and len(resp) > 1 and resp[1] == KC_GET_BATTERY:
        resp = resp[1:]
    if not resp or resp[0] != KC_GET_BATTERY or len(resp) < 6:
        return None
    percentage = resp[1]
    if percentage > 100:
        return None
    voltage = resp[2] | (resp[3] << 8)
    model_id = resp[6] if len(resp) > 6 else 0
    return BatteryReading(
        percentage=percentage,
        voltage_mv=voltage,
        charging=resp[4],
        transport=resp[5],
        timestamp=time.time(),
        model_id=model_id,
    )


def best_device_label() -> str | None:
    """Best-effort human-readable device label from HID enumeration.

    Uses manufacturer/product strings from any Keychron raw-HID interface
    (cable or 2.4 GHz dongle). This is transport-agnostic and does not rely
    on a specific keyboard model.
    """
    if hid is None:
        return None
    try:
        entries = hid.enumerate(VENDOR_ID, 0)
    except Exception:
        return None
    for info in entries:
        if info.get("usage_page") != RAW_USAGE_PAGE or info.get("usage") != RAW_USAGE:
            continue
        product = (info.get("product_string") or "").strip()
        manufacturer = (info.get("manufacturer_string") or "").strip()
        pid = info.get("product_id")
        if product and manufacturer:
            # Avoid duplicating the vendor when product already includes it,
            # e.g. "Keychron Link" with manufacturer "Keychron".
            if product.lower().startswith(manufacturer.lower()):
                return product
            return f"{manufacturer} {product}"
        if product:
            return product
        if manufacturer:
            return manufacturer
        if pid is not None:
            return f"Keychron (PID 0x{pid:04X})"
    return None


class HidUnavailableError(RuntimeError):
    pass


class BatteryReader(threading.Thread):
    """Background thread that pushes BatteryReading objects to a callback."""

    def __init__(self, on_update, on_status=None, pull_interval=5.0, reopen_interval=2.0):
        super().__init__(daemon=True, name="BatteryReader")
        self._on_update = on_update
        self._on_status = on_status or (lambda connected: None)
        self._pull_interval = pull_interval
        self._reopen_interval = reopen_interval
        self._stop = threading.Event()
        self._devices: dict = {}  # path (bytes) -> open hid.device
        self._connected = False

    # -- lifecycle ---------------------------------------------------------
    def stop(self) -> None:
        self._stop.set()

    def _set_connected(self, value: bool) -> None:
        if value != self._connected:
            self._connected = value
            self._on_status(value)

    def _close_devices(self) -> None:
        for dev in self._devices.values():
            try:
                dev.close()
            except Exception:
                pass
        self._devices = {}

    def _drop_device(self, path) -> None:
        dev = self._devices.pop(path, None)
        if dev is not None:
            try:
                dev.close()
            except Exception:
                pass

    def _refresh_devices(self) -> None:
        """Reconcile open devices with the raw-HID interfaces present right now.

        Re-enumerates every cycle so the reader follows transport changes
        (cable <-> dongle <-> Bluetooth) and dongle plug/unplug: it opens newly
        appeared interfaces and closes ones that disappeared. This is essential
        because the dongle's 0xFF60 interface is always present, so we cannot
        rely on "list empty" to trigger a rescan.
        """
        if hid is None:
            return
        try:
            entries = hid.enumerate(VENDOR_ID, 0)
        except Exception:
            entries = []
        present = {
            info["path"]
            for info in entries
            if info.get("usage_page") == RAW_USAGE_PAGE and info.get("usage") == RAW_USAGE
        }
        for path in present:
            if path not in self._devices:
                try:
                    dev = hid.device()
                    dev.open_path(path)
                    dev.set_nonblocking(True)
                    self._devices[path] = dev
                except OSError:
                    continue
        for path in list(self._devices):
            if path not in present:
                self._drop_device(path)
        self._set_connected(bool(self._devices))

    def _send_pull(self) -> None:
        report = bytes([0x00, KC_GET_BATTERY] + [0x00] * REPORT_SIZE)
        for path, dev in list(self._devices.items()):
            try:
                dev.write(report)
            except OSError:
                # Dongle ignores writes; cable answers. Errors -> drop this one.
                self._drop_device(path)

    def _read_all(self) -> None:
        for path, dev in list(self._devices.items()):
            try:
                resp = dev.read(REPORT_SIZE)
            except OSError:
                self._drop_device(path)
                continue
            reading = _parse_report(resp)
            if reading is not None:
                self._on_update(reading)

    def run(self) -> None:
        if hid is None:
            raise HidUnavailableError(
                "Il modulo 'hid' (hidapi) non e' installato. Esegui: pip install hidapi"
            )
        last_pull = 0.0
        last_refresh = 0.0
        while not self._stop.is_set():
            now = time.monotonic()
            if (now - last_refresh) > self._reopen_interval:
                self._refresh_devices()
                last_refresh = now
            if self._devices and (now - last_pull) > self._pull_interval:
                self._send_pull()
                last_pull = now
            self._read_all()
            self._stop.wait(0.05)
        self._close_devices()


def read_once(timeout=4.0) -> BatteryReading | None:
    """Convenience: block until a reading arrives or timeout (CLI/debug use)."""
    result: dict = {}
    done = threading.Event()

    def _cb(reading: BatteryReading) -> None:
        result["reading"] = reading
        done.set()

    reader = BatteryReader(on_update=_cb, pull_interval=0.5)
    reader.start()
    done.wait(timeout)
    reader.stop()
    reader.join(timeout=1.0)
    return result.get("reading")
