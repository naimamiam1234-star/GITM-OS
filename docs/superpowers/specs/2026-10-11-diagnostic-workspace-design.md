# GITM diagnostic workspace
Purpose: turn the existing basic native OBD page into a useful technician workflow on Ubuntu, preserving the separate AutoDiag application.

Scope: validated CAN OBD-II (11/29-bit, ELM protocols 6–9) with per-responder identity, supported-PID discovery, stored/pending/permanent DTC, VIN, readiness monitors, freeze frame 00, selected live sensors and charts. Existing profile/ODX engines remain separate and may not imply universal OEM coverage.

Architecture: obd_session.py owns serialized ELM setup, strict frame parsing, cancellation, scan/live/clear. diagnostic_workspace.py owns background tasks and UI, renders tables instead of raw JSON, never directly sends arbitrary commands. diagnostic_reports.py exports escaped HTML, JSON and timestamped CSV; local store keeps completed scans.

Transport rules: use existing transport.LINK and lock; preserve final headers-off / functional addressing for old read engine. No automatic wireless connections. Missing/negative/invalid/truncated responses remain errors, not zero values or clean bills of health. CAN replies are reassembled independently per ECU with sequence checks. Generic responder does not imply ABS/Airbag scan.

Execution: scans read only. Clear requires explicit user confirmation, stopped RPM for all responding ECUs, a saved pre-clear scan, and post-clear readback. Permanent codes are never promised to clear. No flash/security/key/ADAS/actuator commands synthesized from AI or community data.

UI: Arabic/French/English; summary, codes, live, readiness, freeze, report tabs; visible connection and operation state; cancellation between requests; bounded live history; saves complete/partial scans with provenance. Simulator mode is visible and separated from physical vehicle evidence.

Evidence: unit tests for malformed/interleaved frames, 11/29-bit CAN, readiness bits, negative/no data, cancelled scan, clear refusal; real TCP ELM emulator using existing Link; Qt workflow tests and actual ISO guest verification. Physical vehicle compatibility remains untested.
