"""Smoothing of the noisy battery percentage.

Li-po voltage sags under load and recovers at rest, so the raw percentage
jitters by a few points. We apply:

* an exponential moving average (EMA) on the percentage, and
* a hysteresis deadband on the *displayed* integer, so the shown value only
  moves when the smoothed estimate has drifted past a threshold (or, while
  charging, monotonically follows upward).

This keeps the indicator stable without lying about big real changes.
"""

from __future__ import annotations


class BatterySmoother:
    def __init__(self, alpha: float = 0.3, deadband: float = 1.5):
        # alpha: EMA weight for the newest sample (0..1). Lower = smoother/slower.
        self.alpha = max(0.01, min(1.0, alpha))
        self.deadband = max(0.0, deadband)
        self._ema: float | None = None
        self._displayed: int | None = None

    def reset(self) -> None:
        self._ema = None
        self._displayed = None

    def update(self, raw_percentage: int, charging: bool = False) -> int:
        """Feed a raw percentage, get the value to display."""
        raw = float(max(0, min(100, raw_percentage)))

        if self._ema is None:
            self._ema = raw
        else:
            self._ema = self.alpha * raw + (1.0 - self.alpha) * self._ema

        if self._displayed is None:
            self._displayed = int(round(self._ema))
            return self._displayed

        # Snap to the extremes without waiting (0% and 100% are meaningful).
        if raw >= 100.0:
            self._displayed = 100
        elif raw <= 0.0:
            self._displayed = 0
        elif abs(self._ema - self._displayed) >= self.deadband:
            self._displayed = int(round(self._ema))

        return self._displayed

    @property
    def displayed(self) -> int | None:
        return self._displayed

    @property
    def ema(self) -> float | None:
        return self._ema
