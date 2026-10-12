# Diagnostic Workspace Implementation Plan
> Agentic workers: use executing-plans for inline execution and independent domain agents for UI/audit.
**Goal:** deliver a practical, validated CAN OBD technician workspace in AutoDiag.
**Architecture:** strict per-ECU session engine, native async Qt workspace, independent report exporter and tests; overlay into the verified Ubuntu ISO.
**Tech Stack:** Python standard library, existing transport.Link, PySide6.
**Spec:** docs/superpowers/specs/2026-10-11-diagnostic-workspace-design.md

## Global constraints
Ubuntu x86_64 and native Plasma; AutoDiag separate. No universal/OEM capability claims. Serialize adapter operations. Arabic/French/English. Keep last verified download available.
## Review focus
Interleaved CAN frames cannot merge ECUs. Unavailable response cannot become clean state. Cancel/close cannot destroy running QThread. Clear refuses missing/running RPM. Export escapes vehicle/ECU text and records measured timestamps.

### Task 1: Session engine
Files diag-integration/obd_session.py, tests/test_obd_session.py.
Interfaces Session(link).scan(vehicle={},cancel=None,progress=None)->dict; live(pids:list[int],cancel=None)->list[dict]; clear(confirm:bool,vehicle={},cancel=None)->dict; parse_can(raw,protocol)->dict[str,bytes].
- [x] Write failing parser and TCP ELM tests; verify failures.
- [x] Implement per-ECU CAN reassembly, standard PID decoders, readiness, scan, cancellation and verified clear.
- [x] Run unittest with real loopback TCP Link, include malformed/negative/29-bit/timeout tests.
### Task 2: Workspace and exports
Files diagnostic_workspace.py, diagnostic_reports.py, tests/test_workspace.py, tests/test_reports.py.
- [x] Write failing export and async workflow tests.
- [x] Implement summary/DTC/live/readiness/freeze/report tabs, bounded charts and recording, cancel, connection and no duplicate tasks.
- [x] Run offscreen Qt and real emulator workflow tests; inspect renders.
### Task 3: ISO integration
Files diag-integration/install.py and workflow/installer overlays.
- [x] Patch diagnosis_page and engines_page into tested workspaces; preserve existing service and AI pages.
- [x] Run installed-source tests, simulate scan in guest and capture workspace.
- [x] Build BIOS/UEFI ISO; publish preview only after same-commit evidence and full download digest checks.
