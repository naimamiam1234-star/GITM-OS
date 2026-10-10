# GITM native appearance integration

The Ubuntu/Plasma preview uses pinned open-source components:

- Klassy: `9b788b2ea8d40c6a7af3b0130de9e891d41fbb30` (Qt 6.10+, KF6 6.22+, Plasma 6.6).
- Panel Colorizer: `d0b1d4cab773f05cdcda2c1b2970093a5c367b54`.
- Papirus: Ubuntu's packaged icon theme.

Upstream source URLs and licence notices are preserved under `/usr/share/doc/gitm-theme`.

The bottom panel is a centered, floating, fit-content auto-hide dock containing launchers and native icon tasks; the repeated bottom clock and system tray are removed. Settings entry points route to native System Settings with one process key; module requests are forwarded to the application's existing instance. The former custom settings and appearance dialogs are removed. Native child processes do not inherit the Python runtime's Fusion/generic overrides. KDE background colour changes synchronize the desktop's light/dark mode. KCalc remains the native desktop calculator; AutoDiag's workshop tools remain scoped to AutoDiag.

Regression checks: `check-contract.py` and `check-launches.py`. The latter exercises repeated settings launch paths with an isolated process fake, without changing the host's desktop. Actual guest gallery capture records `GITM_SETTINGS_WINDOWS|1` after repeated activation; BIOS/UEFI and native windows must still be validated separately.

ISO success and download checks do not establish installation, physical device compatibility, update installation or OEM vehicle function support.
