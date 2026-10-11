# GITM OS — anchored quick settings preview

Ubuntu 26.04 amd64 with native Plasma 6.6.6 / KWin, pinned Klassy decoration and Panel Colorizer, Papirus icons, Firefox, and the separate GITM AutoDiag application.

Top-bar Wi-Fi, Bluetooth, audio and power icons open frameless dropdown cards under their anchors. Cards close with Escape or outside click; only one is open at a time. Full settings use explicit secondary buttons.

Quick Settings includes Wi-Fi/Bluetooth status, airplane mode, day/night appearance, screenshot and lock shortcuts, hardware-supported brightness, sound level and power actions. Power actions require a second explicit confirmation inside the dropdown. Missing adapters and audio outputs show unavailable status.

Validation: BIOS and UEFI desktop boot, guest repository/catalogue evidence, actual application screenshots, and physical QMP input for search and popup dismissal. Manifest and public download checks refer to this source commit.

Development preview: physical installation, update installation, wireless discovery/connection/pairing, screen lock, brightness, and suspend/power commands need compatible real-hardware validation. VM screenshots without adapters do not prove wireless support. OEM vehicle functions require adapter/vehicle-specific implementation and verification.

CPU: SSSE3, SSE4.1, SSE4.2 and POPCNT required by bundled Qt. Live changes require persistence or installation to survive reboot. Native dock is visible by default; optional auto-hide is not validated.

ISO parts have per-part and whole-image SHA-256. The preview service streams the joined ISO with resume support; gallery images are actual guest captures.

Screenshot tool: Ubuntu's kde-spectacle package supplies /usr/bin/spectacle.
