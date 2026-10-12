# Professional Interface Implementation Plan
> Agentic workers: use executing-plans for root coordination and independent parallel domain workers. User has authorized implementation of the attached written design review.
**Goal:** implement the approved professional interface on the existing working diagnostic application.
**Architecture:** shared component/style API and shell wrap existing Window; independent page factories reuse tested engines. Preserve the diagnostic overlay install path and real guest evidence.
**Tech:** Python/PySide6, SQLite, existing ELM engine, native Plasma.
**Spec:** docs/superpowers/specs/2026-10-12-professional-interface-design.md
## Constraints
Ubuntu, separate AutoDiag, ar/fr/en, bounded worker lifetimes, no invented vehicle readings/coverage, no cloud sending without consent, no CAN transmissions. Native fullscreen only; normal dock preserved. Body16px minimum. Shared APIs are fixed by spec.
## Review focus
Stale cached page after navigation; root footer exposing stale vehicle measurements; report comparison mixing simulator/physical; AI attachment VIN/client leakage; controls inaccessible at1024px/RTL. Tests below own each condition.
### Task1 Shared shell/components (root)
Files professional_components.py, professional_ui.py, tests/test_professional_ui.py, install.py.
- [ ] Tests for sidebar navigation/cache lifetime, unknown metrics, light/dark focus, no plain split strip, fullscreen restore and layout containment at all four sizes.
- [ ] Implement component API from spec; install(window)->None wrapper, refresh()->None, navigation preserving live-worker cancellation. Factories are each module.show(window)->QWidget, use window.page(title).
- [ ] Root installer wraps end of Window.__init__ with professional_ui.install(self); wires page callbacks and copies modules after tested baseline overlay. Idempotence/source-drift checks.
### Task2 Diagnostic page (domain worker)
Files diagnostic_workspace.py, tests/test_workspace.py.
- [ ] Action-state tests: empty/disconnected export/clear disabled, cancel only running; unknown metrics not0; partial scan not clean; filters keep raw reports; selected ECU identity stable.
- [ ] Restructure layout with shared cards, bounded progress and compact tabs. Keep Session/Worker/export/cancellation implementation and all existing tests.
### Task3 VCI/vehicle pages (domain worker)
Files vci_workspace.py, vehicle_workspace.py, tests/test_connection_vehicle.py.
- [ ] Tests for passive inventory/no auto handshake, labeled form selection, disconnected readings absent, capture form values before workers, persist selected year/engine, logo geometry at1024 and1280.
- [ ] Implement show(window)->QWidget for both using actual transport.inventory/LINK and explicit source_gateway consent, no engine modifications.
### Task4 Reports/AI/updates (domain worker)
Files workshop_workspace.py, ai_workspace.py, update_workspace.py, tests/test_workshop_ui.py.
- [ ] Test real DB filtering/comparison, export selected record, simulator labeling, API key stays session-only, scan attachment preview redacts VIN/client, cloud request only explicit consent, signed package gating.
- [ ] Implement actual history/details/export/QtPDF/print; streaming ChatTask UI, explicit sanitized attachment preview; preserve signature/update rollback backend and open native Discover for system updates.
### Task5 Useful tools/unsupported pages (root or independent worker)
Files can_workspace.py, support_workspace.py, tests/test_can_ui.py.
- [ ] Test strict classic/FD frame decoding, CSV bounds/invalid input, receive-only SocketCAN, no fabricated unavailable TPMS/service values.
- [ ] Implement read-only CAN capture/offline CSV and explicit unsupported/hardware requirement cards.
### Task6 QA/release(root+independent review)
- [ ] Run full suite using PYTHONPATH=ui-work/diag-integration:source/GearDiag-Raw-Build/app:runtime and QT_QPA_PLATFORM=offscreen. No skipped tests.
- [ ] Inspect local native screenshots all major pages/themes/resolutions. Resolve meaningful failures before build; independent review.
- [ ] Pin last verified source38171155293, new release tagplasma11, extend exact guest gallery and package count. Run installed-suite and BIOS/UEFI before publishing.
- [ ] Deploy verified manifest to preview worker; verify full download/hash/ranges/gallery; record evidence and deliver links. Keep physical hardware limitations explicit.
