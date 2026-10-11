# AutoDiag validation — 2026-10-11
Release: [gitm-os-3.3.0-plasma10](https://github.com/naimamiam1234-star/GITM-OS/releases/tag/gitm-os-3.3.0-plasma10).
Source commit: `dba86063c3ea29b1cdfc4ad1480f510fce9feb85`.

- Installed-module suite: 57 tests passed; skipped tests rejected. [Build and BIOS/UEFI run](https://github.com/naimamiam1234-star/GITM-OS/actions/runs/38171155293).
- Actual guest loopback ELM fixture: multiframe DTC scan, live readings, CSV recording and HTML/JSON exports passed. Fixtures explicitly identify simulator data.
- [Publisher validation](https://github.com/naimamiam1234-star/GITM-OS/actions/runs/38171155346): source digest, guest evidence, single settings window, real desktop input and popups verified; gallery contains 68 actual captured images.
- [Public download verification](https://github.com/naimamiam1234-star/GITM-OS/actions/runs/38172792415): full 3469529088-byte ISO, SHA256, resumable ranges, split boundaries, stale If-Range protection and gallery digest passed.

ISO SHA256: `af1d4a8d227463e03147486280b2e09847877d8a00ad21872f1f2cd3ad8603cd`.
Gallery SHA256: `e293e2ccfb64d6988142480fc870c065a534dbafffae97203cdbfb579f26f0b5`.

Readiness regressions were reproduced before correction: unsupported monitors never claim completion. DTC acquisition status means successful reading, not absence of faults. Raw UTC timestamps and simulator/session provenance remain in exports. CAN responders are never merged.

Manually reviewed earlier actual guest pages and revised local readiness UI. Final gallery was captured and checked by the release pipeline; the final local browser inspection was unavailable after the workspace environment disconnected.

Coverage: generic emissions CAN OBD, supported PID/readiness/freeze-frame data, local reports and read-only documented ECU profile imports. Physical cars and serial/Bluetooth/BLE hardware remain untested. OEM coding/flashing, active tests, maintenance procedures, keys, TPMS, ADAS and EV-specific operations are not validated or supplied by this addition. See diag-integration/COVERAGE.md.
