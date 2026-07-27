# Release Notes

## v1.0.3

### What's new

- Added full Keychron Q1 HE support in the firmware flasher: ANSI Knob, ISO Knob and JIS Knob cable-mode USB PIDs are now recognized before entering DFU.
- Fixed Q1 HE model naming over USB when the patched firmware reports `model_id = 2`, so the Device view shows "Keychron Q1 HE" on USB as well as Bluetooth and 2.4 GHz.
- Added explicit Windows shutdown/logoff handling for the tray app.
- During Windows session end, Keyboard Companion now accepts shutdown immediately and exits through a fast path that skips slow UI, tray, logging, and device-name refresh work.
- Added lightweight shutdown diagnostics in `%APPDATA%\KeyboardCompanion\shutdown_log.txt`.

## v1.0.2

- Fixed a rare crash when opening the firmware flash wizard from the Firmware tab while the main app window was still open.
- The Firmware tab now closes the main window before launching the dedicated flash wizard, avoiding multiple Tk roots running in separate threads on Windows.
- Added Companion recognition for Q1 HE firmware battery reports, so 2.4 GHz dongle readings can show "Keychron Q1 HE" instead of the generic dongle name when the keyboard firmware reports model id 2.
