"""Small Tk settings window, opened from the tray menu.

Runs its own Tk root + mainloop in a dedicated thread (the tray owns the main
thread on Windows). Kept intentionally simple and dependency-free (tkinter is
bundled with CPython).
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from . import APP_NAME, autostart, i18n


def open_settings(app) -> None:
    cfg = app.config

    root = tk.Tk()
    root.title(i18n.t("settings_title", app=APP_NAME))
    root.resizable(False, False)
    try:
        root.attributes("-topmost", True)
    except tk.TclError:
        pass

    frame = ttk.Frame(root, padding=16)
    frame.grid(row=0, column=0, sticky="nsew")

    lang_codes = [code for code, _ in i18n.available_languages()]
    lang_labels = [label for _, label in i18n.available_languages()]

    lang_var = tk.StringVar(value=i18n.language_label(i18n.get_language()))
    notify_var = tk.BooleanVar(value=bool(cfg["notify_low_battery"]))
    threshold_var = tk.IntVar(value=int(cfg["low_battery_threshold"]))
    alpha_var = tk.DoubleVar(value=float(cfg["smoothing_alpha"]))
    autostart_var = tk.BooleanVar(value=autostart.is_enabled())

    # Keep references so we can re-translate labels live on language change.
    lbl_language = ttk.Label(frame)
    lbl_threshold = ttk.Label(frame)
    chk_notify = ttk.Checkbutton(frame, variable=notify_var)
    lbl_smoothing = ttk.Label(frame)
    chk_autostart = ttk.Checkbutton(frame, variable=autostart_var)
    lbl_note = ttk.Label(frame, foreground="#666", wraplength=320)
    btn_save = ttk.Button(frame)
    btn_close = ttk.Button(frame)

    def retranslate() -> None:
        root.title(i18n.t("settings_title", app=APP_NAME))
        lbl_language.config(text=i18n.t("settings_language"))
        lbl_threshold.config(text=i18n.t("settings_threshold"))
        chk_notify.config(text=i18n.t("settings_notify"))
        lbl_smoothing.config(text=i18n.t("settings_smoothing"))
        chk_autostart.config(text=i18n.t("settings_autostart"))
        lbl_note.config(text=i18n.t("settings_note"))
        btn_save.config(text=i18n.t("settings_save"))
        btn_close.config(text=i18n.t("settings_close"))

    def on_language_changed(event=None) -> None:
        try:
            idx = lang_labels.index(lang_var.get())
        except ValueError:
            return
        app.set_language(lang_codes[idx])
        retranslate()

    combo = ttk.Combobox(
        frame, textvariable=lang_var, values=lang_labels, state="readonly", width=18
    )
    combo.bind("<<ComboboxSelected>>", on_language_changed)

    spin = ttk.Spinbox(frame, from_=1, to=99, textvariable=threshold_var, width=6)
    scale = ttk.Scale(frame, from_=0.05, to=1.0, variable=alpha_var, orient="horizontal", length=200)

    def on_save() -> None:
        cfg["notify_low_battery"] = bool(notify_var.get())
        try:
            cfg["low_battery_threshold"] = int(threshold_var.get())
        except (tk.TclError, ValueError):
            pass
        cfg["smoothing_alpha"] = round(float(alpha_var.get()), 2)
        autostart.set_enabled(bool(autostart_var.get()))
        app.apply_settings()
        root.destroy()

    btn_save.config(command=on_save)
    btn_close.config(command=root.destroy)

    # Layout.
    lbl_language.grid(row=0, column=0, sticky="w", pady=4)
    combo.grid(row=0, column=1, sticky="e", pady=4)
    lbl_threshold.grid(row=1, column=0, sticky="w", pady=4)
    spin.grid(row=1, column=1, sticky="e", pady=4)
    chk_notify.grid(row=2, column=0, columnspan=2, sticky="w", pady=4)
    lbl_smoothing.grid(row=3, column=0, sticky="w", pady=4)
    scale.grid(row=3, column=1, sticky="e", pady=4)
    chk_autostart.grid(row=4, column=0, columnspan=2, sticky="w", pady=4)
    lbl_note.grid(row=5, column=0, columnspan=2, sticky="w", pady=(10, 8))
    btn_save.grid(row=6, column=0, sticky="w", pady=(4, 0))
    btn_close.grid(row=6, column=1, sticky="e", pady=(4, 0))

    retranslate()

    root.update_idletasks()
    root.mainloop()
