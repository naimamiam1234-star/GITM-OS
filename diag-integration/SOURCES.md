# Sources and implementation provenance

The new session, simulator, reports and native workspace are GITM project code. They use Python's standard library and the existing PySide6 runtime; no third-party package or proprietary OEM database was copied into this overlay.

Protocol references reviewed:
- ELM Electronics ELM327 data sheet: https://www.elmelectronics.com/wp-content/uploads/2017/01/ELM327DS.pdf — ATH1/CAF1, CAN responder headers and independent multiframe sequences.
- python-OBD documentation: https://python-obd.readthedocs.io/en/latest/Command%20Tables/ — generic OBD modes, units and supported PID selection.
- python-OBD decoder reference: https://github.com/brendan-w/python-OBD/blob/master/obd/decoders.py — checked readiness bit positions and standard PID formulas; implementation is independently written.
- ELM327 emulator reference: https://github.com/Ircama/ELM327-emulator — multi-ECU bench-testing approach. The included loopback fixture is independently written and explicitly identifies itself as GITM_SIMULATOR.

Existing imported DDT/ODX datasets and libraries retain their original notices in the original application. A dataset import does not grant redistribution rights or prove vehicle coverage.
