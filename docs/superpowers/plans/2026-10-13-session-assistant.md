# AutoDiag session assistant implementation

Goal: implement the user-approved session assistant design without rebuilding GITM OS.

Architecture: immutable de-identified snapshots from existing measured OBD state; one cached side panel; separate cloud and retrieval threads; append-only SQLite assistant journal; native browser opens selected references without navigating the diagnosis page.

Tech stack: existing Python/PySide6, SQLite, urllib, OpenRouter, Brave Search API and YouTube Data API.

Spec: latest user message explicitly approves the session assistant, three actions and browser integration. User authorization permits inline implementation and normal repository/Drive delivery.

Global constraints: preserve actual report vehicle, ECU attribution and simulator label; no adapter imports in assistant core; no generated vehicle commands; no credentials on disk or in logs; explicit preview/consent for external requests; no claims of full web-page or video/transcript analysis from snippets. Keep the original OS signing key and existing runtime.

Tasks:
1. Restore verified 3.3.1 baseline and run all 158 existing tests. Add failing snapshot, journal, retrieval and side-panel tests.
2. Implement assistant_core snapshots, bounded API mapping, public source URL checks and session-isolated SQLite journal. Verify no provider calls without key/consent.
3. Implement cached session_assistant panel, top button, full-workspace expansion, existing OpenRouter assistant on separate worker, native browser integration and source journal. Test page/selection retention and no adapter traffic.
4. Add contextual DTC/live actions, preserve selected ECU, restore journal sources. Exercise actual TCP simulator while the panel is open; inspect light/dark screenshots.
5. Build version 3.3.2-1 application-only package from the existing verified OS; test installation/reboot, publish package/checksum and actual screenshots. Do not create an ISO.

Review focus: cross-session contamination, mixed ECU evidence, accidental external sends, running-thread shutdown, source claims, narrow-window overflow and unchanged update trust key.

Next phase: sourced waveform/document selection and repair-order attachments, then guided actuator tests only with vehicle-specific definitions and independently verified prerequisites. Voice input remains a later feature.
