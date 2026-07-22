# Release Notes

## v1.0.2

- Fixed a rare crash when opening the firmware flash wizard from the Firmware tab while the main app window was still open.
- The Firmware tab now closes the main window before launching the dedicated flash wizard, avoiding multiple Tk roots running in separate threads on Windows.
- Added Companion recognition for Q1 HE firmware battery reports, so 2.4 GHz dongle readings can show "Keychron Q1 HE" instead of the generic dongle name when the keyboard firmware reports model id 2.
