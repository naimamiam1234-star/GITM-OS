# Professional interface preview — verified 2026-10-12

Release: gitm-os-3.3.0-plasma11
Source commit: 7b67b1d154692133cd256e94e63ee9cf704207e1
ISO build/BIOS/UEFI/gallery run: 38190430931 (success)
Evidence/keyboard/publisher run: 38190430934 (success)
Public download run: 38191888970 (success)

ISO bytes: 3469848576
ISO SHA-256: 338eab476cce1ee47f4dc651e6e927c3cc02829db96cf16529c32a91448857c8
Gallery: 70 actual images, 39058817 HTML bytes, SHA-256 814c9f3dcec9e883795603ab715d0f2397f23ba654269edc79ff3e6e19feb79a.

Implemented native cached navigation, measured context, light/dark themes, Arabic/French/English, DTC filters, per-ECU live plots and bounded recording, readiness states, freeze-frame cards and same-session split view. Vehicle context changes cannot relabel an old report or continue its live reads. Closing a cloud request defers destruction until the worker finishes.

Workshop: explicit customer/car selection, plates and multiple vehicles, precise invoice arithmetic and preserved legacy currencies/statuses, vehicle-checked report association, PDF/print exports. Reports retain immutable acquisitions and store private local notes/validated images separately. General calculator, PDF, media, camera, settings and updates are shared GITM OS services.

Evidence: 123 tests passed without skips both locally and in the installed ISO modules. Local four-resolution light/dark layouts, live language switching and fullscreen/Escape restore passed. Actual ISO screenshots reviewed for dashboard, live readings, readiness, customers, invoices and OS camera/update windows. Native bottom dock does not cover the maximized diagnostic workspace. Loopback ELM simulator scan/multi-frame DTC/live recording/export passed in the guest; all simulator observations remain labelled.

The public check streamed the entire ISO and matched size/SHA-256; checked ISO signature, HEAD, split-boundary/suffix/invalid ranges, If-Range revision protection and gallery digest/count.

Limits: physical vehicles/adapters/CAN interfaces/camera capture remain untested. Camera guest evidence is its genuine no-device state, not successful physical capture. No universal OEM coding/flashing/active tests, 41 maintenance functions, TPMS/ADAS/keys/EV coverage or accounting compliance certification. Source import and recalled data do not certify applicability. CPU requires SSSE3/SSE4.1/SSE4.2/POPCNT for bundled Qt. This remains a development preview.

Download: https://gitm-os-plasma-preview.naimamiam1234.workers.dev/GITM-OS-Plasma6-amd64.iso?revision=plasma11
Gallery: https://gitm-os-plasma-preview.naimamiam1234.workers.dev/gallery?revision=plasma11
