"""Render the tray icon: a battery glyph with the percentage drawn inside."""

from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

SIZE = 64


def _level_color(percentage: int | None, charging: bool) -> tuple:
    if charging:
        return (60, 190, 90)      # green while charging
    if percentage is None:
        return (130, 130, 130)    # grey when unknown
    if percentage <= 15:
        return (220, 70, 60)      # red
    if percentage <= 35:
        return (230, 170, 50)     # amber
    return (90, 200, 120)         # green


def _load_font(size: int):
    for name in ("segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def make_icon(percentage: int | None, charging: bool = False, connected: bool = True) -> Image.Image:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    color = _level_color(percentage, charging)
    outline = (235, 235, 235)

    # --- Battery glyph: upper area, a bit larger ---
    body = (7, 4, 51, 30)            # x0, y0, x1, y1
    d.rounded_rectangle(body, radius=5, outline=outline, width=3)
    d.rounded_rectangle((51, 12, 57, 22), radius=2, fill=outline)  # + terminal

    # Fill proportional to charge.
    if percentage is not None and connected:
        inner_left, inner_top, inner_right, inner_bottom = 11, 8, 47, 26
        span = inner_right - inner_left
        fill_w = int(span * max(0, min(100, percentage)) / 100)
        if fill_w > 0:
            d.rounded_rectangle(
                (inner_left, inner_top, inner_left + fill_w, inner_bottom),
                radius=3,
                fill=color,
            )

    # Charging bolt over the battery.
    if charging:
        d.polygon([(31, 6), (24, 19), (29, 19), (26, 29), (37, 15), (31, 15)],
                  fill=(255, 220, 60))

    # --- Percentage text: lower area, separated, larger ---
    if percentage is None or not connected:
        label = "--"
    else:
        label = str(percentage)
    # Shrink only for 3 digits ("100") so it still fits the 64px canvas.
    font = _load_font(30 if len(label) >= 3 else 38)
    bbox = d.textbbox((0, 0), label, font=font)
    tw = bbox[2] - bbox[0]
    x = (SIZE - tw) / 2 - bbox[0]
    y = 62 - bbox[3]                 # bottom-align near the canvas bottom
    d.text((x, y), label, font=font, fill=outline)

    return img
