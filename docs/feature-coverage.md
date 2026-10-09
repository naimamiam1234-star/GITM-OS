# Feature acceptance matrix

| Function | Included implementation | Outstanding validation/dependency |
| --- | --- | --- |
| GITM desktop | Native Qt launcher, glass cards, wallpaper, settings, search, dock | BIOS/UEFI boot recorded by current workflow |
| Installer | Calamares, partitioning and GRUB modules | Full disk install and installed-system reboot |
| Auto Scan | Generic OBD discovery and profile-driven read-only ECU scan | Exact vehicle profiles and real adapter tests; not every vehicle module |
| Live Data | Supported OBD PID decoding and split view RPM trend | Actual vehicle response and adapter performance |
| ECU Coding | Definition import/reference only | OEM procedures, permissions, compatible adapter and testing |
| Active Tests | Definition/reference only | Vehicle-specific executable procedure and validation |
| Service Functions | Descriptive catalogue, not a universal executable set | Implement/test each ECU-specific procedure |
| AI Diagnostics | Authenticated Cloudflare UI | Sign-in and authenticated provider response test |
| Dual Diagnosis | Two independent app processes, explicit secondary pairing, adapter reservation | Two physical adapters and simultaneous vehicle test |
| Split Screen | Resizable DTC/live-data views with measured RPM trend | Hardware trend validation |
| TPMS / ADAS / Keys | Reference/availability states | Specialized equipment, procedures and authorization |
| EV Diagnostics | CAN tools and definition framework | EV-specific packs and validation |
| Reports / workshop | SQLite history, customers, PDF invoices, export | User acceptance and backup policy |
| App updates | Original signature trust, install/health/rollback engine, release launcher | Signed update using owner's private key and production delivery |
| OS updates | Ubuntu package manager and Discover | Post-install complete update/reboot test; no whole-image update claim |

Software/interface checks and offline decoding tests cannot establish physical
vehicle support. The current workflow's result is authoritative for ISO boot.
