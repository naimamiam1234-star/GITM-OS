# GITM OS — AutoDiag diagnostic workspace preview

Built on Ubuntu with native Plasma/KWin, keeping AutoDiag separate. Includes the verified popup controls from preview8.

New native AutoDiag workspace: CAN OBD per-responder scan, stored/pending/permanent DTC, VIN, readiness, freeze frame00, 27 numeric PID decoders, live graph and bounded CSV recording, offline HTML/JSON exports, local scan persistence. Documented ECU profile reads are now accessible in the native app with exact make/model/year/engine gates. UDS response validation and adapter cleanup corrected.

Verification: installed-module test suite, real loopback TCP ELM transport including11/29-bit CAN and repeated addressed reads, actual ISO guest simulator scan/live/export, BIOS/UEFI visible Plasma session, keyboard/popups and full public download SHA256/range tests. Screenshot gallery includes explicitly labeled simulator data.

Known limits: no physical vehicle, serial/Bluetooth/BLE adapter, OEM coverage, flash/coding/active test, 41 maintenance, TPMS/ADAS/key/EV-specific function validation. No OEM ECU definitions bundled. Cross-packet UDS P2* pending wait not implemented. Generic OBD is emissions scope only. Requires SSSE3/SSE4.1/SSE4.2/POPCNT CPU features for bundled Qt. This is a development preview, not proof of universal diagnostic coverage.

