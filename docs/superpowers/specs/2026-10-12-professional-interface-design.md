# GITM AutoDiag Professional Interface

Approved input: the user's 2026-10-11 Arabic design review and explicit implementation approval on 2026-10-12. This is an internal implementation of that approved design, not a new permission request.

Ubuntu x86_64, native Plasma/KWin, PySide6 Widgets. Preserve the tested CAN OBD engine, serialized adapter access, worker cancellation and offline evidence. Arabic RTL, French and English; keyboard, pointer and touch. Target 1280x800; also1024x768,1366x768,1920x1080.

## Shared shell and components
One compact header: GITM identity, current page, search, language, theme, split menu and notifications. Collapsible grouped sidebar and compact grouped dashboard. Existing20 home launchers remain accessible to preserve coverage and gallery automation. No persistent Split Screen/Dual Diagnosis strip. Footer shows real transport state, selected vehicle, established protocol and measured voltage only when available. The physical measurement timestamp/provenance is retained; unknown is not0. Fullscreen(F11) uses native window fullscreen, Escape restores; Plasma dock policy hides behind active windows without removing users' normal desktop dock.

Light/dark/auto tokens, 16px body minimum, visible focus, >=40px actions, consistent SVG icons. Components module supplies triple(ar,fr,en), MetricCard(title,value='—',detail=''), InfoCard(title) with body QVBoxLayout, action_button(text,role='secondary',icon=None), configure_table(table). Root shell owns style application; page modules use roles/objectNames, not private white styles. Retain system font/Tajawal already packaged; custom fonts are optional, never downloaded at runtime.

## Pages
Diagnostic workspace: vehicle/connection strip, measured metric cards, prioritized scan action, cancel visible only during operation, export requires results, clear is warning action gated by valid connected scan; engine retains mandatory pre-clear/RPM/readback. DTC filtering, progress without invented completion percentages, stable ECU graph selection, saved scans and structured errors. Preserve all57 tests.

VCI: labeled USB/Bluetooth/TCP forms, passive device inventory, explicit connect/disconnect, identity and log cards. Never handshake unknown devices automatically; no fabricated firmware/voltage or support for J2534/TCS just because USB was found.

Vehicle: search, bounded aspect-preserved logos, adaptive4/5-column grid, persistent explicit make/model/year/engine/VIN selection, exact profile support limitations. VIN network lookup only on explicit consent.

Reports/history: filtered table of real SQLite records, split details, HTML/JSON/CSV exports, PDF/print from supported Qt APIs, comparison of two selected real OBD sessions. Empty state useful; simulator evidence visibly separated. No invented customers/scan examples. AI: conversation with vehicle context, session-only password-masked API key, actual OpenRouter streaming/cancel preserved, preview and explicit consent before attaching de-identified scan data. No automatic VIN/client transfer, no diagnostic write actions from AI.

Updates: separate native system updater and signed .gitmupdate application packages. Preserve existing signature/rollback engine; readable summaries, raw details behind expandable developer section, no automatic installation.

Maintenance/TPMS: grouped informative cards and hardware/definition requirements, visibly unavailable until implementation/physical validation. No bogus41 service actions or wheel measurements. CAN tools may add explicitly read-only SocketCAN capture and offline frame CSV analysis if locally testable; no raw frame transmission or guessed DBC decoding. Knowledge and workshop legacy tools keep existing functions with common framing; do not replace working backends with mockups.

## Validation/release
Meaningful red-green tests for new navigation/action state, unknown-value handling, recording/selection/provenance, cloud consent/redaction, imports and capture bounds. Local native screenshots at four resolutions and both themes, keyboard/RTL checks. Independent code review before build. One consolidated source commit triggers ISO build, installed tests, BIOS/UEFI and actual guest gallery. Publish next preview only after source and publisher pass; then full public ISO SHA256/range/gallery verification. Physical hardware remains untested and documented.
