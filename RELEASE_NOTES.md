# Release Notes

## v1.0.2

- Fixed a rare crash when opening the firmware flash wizard from the Firmware tab while the main app window was still open.
- The Firmware tab now closes the main window before launching the dedicated flash wizard, avoiding multiple Tk roots running in separate threads on Windows.
