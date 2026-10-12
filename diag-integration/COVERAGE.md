# Diagnostic coverage and evidence

Implemented: ELM/STN over existing USB serial, TCP Wi-Fi, paired RFCOMM and BLE transport paths; new session requires CAN OBD protocols 6–9 (250/500 kbit/s, 11/29-bit). Transport availability is adapter dependent. ECU responder IDs stay separate. Generic emissions OBD does not identify manufacturer module roles.

Read paths: VIN, stored/pending/permanent emissions DTC, supported PID maps through 60h, 27 standard numeric PID decoders, readiness/MIL, freeze frame 00 through PID20h, selected live readings, graph, bounded CSV recording, local scan persistence, HTML/JSON/CSV exports.

Clear: explicit confirmation, saved pre-clear scan with valid stored DTC discovery, all discovered responders reporting zero engine RPM, acknowledgement and post-clear stored/pending readback. Missing acknowledgement returns uncertainty even if post-read is clean. Permanent DTC are not cleared by this operation. Unsupported optional VIN/permanent/freeze data remain acquisition errors.

Documented ECU profiles: explicit JSON import, exact make/model/year/engine match, declared physical CAN IDs, read-only identification / UDS DTC / defined live DID paths. No OEM profiles are shipped. Imported definitions and author claims are not independent vehicle validation. Pending NRC78 is retained unless the final response is already in the same input; full cross-packet P2* waiting is not implemented.

Verified locally: strict ISO-TP parser, interleaved responders, 11/29-bit TCP ELM sessions, malformed/truncated responses, cancellation, clear refusal/readback/uncertainty, real TCP profile and repeated imported reads, Qt worker lifecycle, recorder bounds and escaped exports. ISO verification adds guest simulator sessions and BIOS/UEFI evidence from the exact release.

Not established: compatibility with any physical vehicle/ELM clone; real serial/Bluetooth/BLE transport hardware; manufacturer all-ECU coverage; coding/flashing/active tests/41 maintenance functions; key/TPMS/ADAS/EV-specific operations; actual workshop repairs. These need appropriate hardware, lawful licensed definitions, documented procedures and physical validation.
