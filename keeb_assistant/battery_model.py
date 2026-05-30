"""Host-side battery percentage model (charging compensation).

The keyboard derives its percentage from the *instantaneous* battery voltage.
While charging, the terminal voltage is inflated (IR rise during constant
current + the charger holding it high in constant voltage), so that percentage
overestimates the true resting state of charge.

Measured on a real K10 HE at ~76% SoC: a charging plateau of ~4050 mV relaxed
to ~3932 mV at rest once unplugged (~118 mV, ~16 percentage points). So while
*actively* charging we subtract a voltage offset before mapping to %, which
approximates the open-circuit (resting) voltage.

Only the value shown to the user is affected. The raw voltage/percentage that
the logger writes to the CSV are left untouched, so calibration data stays a
clean ground truth and the offset can be refined later from real samples.
"""

from __future__ import annotations

# Mirror the firmware thresholds (keychron/common/wireless/battery.{c,h}).
FULL_VOLTAGE_MV = 4100
EMPTY_VOLTAGE_MV = 3500
SHUTDOWN_VOLTAGE_MV = 3300

# Charge state (report byte 4): 0 = on battery, 1 = charging, 2 = full.
CHARGING_NONE = 0
CHARGING_ACTIVE = 1
CHARGING_FULL = 2

# Empirical starting point from the first CSV (~76% SoC). Refine from more data.
DEFAULT_CHARGE_OFFSET_MV = 120


def voltage_to_percentage(mv: int) -> int:
    """Replicate the firmware's piecewise voltage -> percentage mapping."""
    if mv >= FULL_VOLTAGE_MV:
        return 100
    if mv > EMPTY_VOLTAGE_MV:
        span = FULL_VOLTAGE_MV - EMPTY_VOLTAGE_MV
        return int(round((mv - EMPTY_VOLTAGE_MV) * 80 / span + 20))
    if mv > SHUTDOWN_VOLTAGE_MV:
        span = EMPTY_VOLTAGE_MV - SHUTDOWN_VOLTAGE_MV
        return int(round((mv - SHUTDOWN_VOLTAGE_MV) * 20 / span))
    return 0


def corrected_percentage(
    voltage_mv: int,
    raw_percentage: int,
    charging: int,
    *,
    enabled: bool = True,
    offset_mv: int = DEFAULT_CHARGE_OFFSET_MV,
) -> int:
    """Return a charging-compensated percentage for *display only*.

    Falls back to the keyboard's own percentage when:
    * correction is disabled,
    * not actively charging (on battery, or already full), or
    * no voltage is available (e.g. the Windows/BLE mirror sends voltage_mv=0).

    The correction can only lower the charging reading toward its resting value,
    never raise it above what the keyboard reports.
    """
    if not enabled or charging != CHARGING_ACTIVE or voltage_mv <= 0:
        return raw_percentage
    adjusted = voltage_to_percentage(max(0, voltage_mv - offset_mv))
    return min(adjusted, raw_percentage)
