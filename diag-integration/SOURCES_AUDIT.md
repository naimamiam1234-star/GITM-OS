# Local source audit — 12 October 2026 (UTC)

The 35 catalog entries remain reference links with `integration_verified: false`.
They are separate from inspected bundled software licenses and a tested software
loading path. Neither a URL nor a bundled library establishes OEM data rights,
manufacturer coverage, or successful vehicle communication.

| Item | Local evidence | Verified scope |
| --- | --- | --- |
| odxtools 11.6.2 | Bundled METADATA and MIT LICENSE; direct import in `odx_engine.library()` | Actual bundled dependency loads; `load_file` exists. No parsing/codec/vehicle result claimed by this audit. |
| python-can 4.6.1 | Bundled METADATA says LGPL-3.0-only; LICENSE.txt contains LGPL v3 | Bundled downstream dependency used in odxtools `isotp_state_machine` and `cli/snoop`; no direct app import. GITM transport does not use this library. No transport test claimed. |
| can-isotp, udsoncan, doipclient | No matching app-level AST imports | Reference-only here; licenses and integrations not inspected or tested. |

`source_audit.json` records the date, versions, evidence paths and SHA-256 hashes,
plus the exact nonrecursive app import scan scope. The scan covers `app/*.py`;
vendor implementations are inspected separately and are not counted as app
integrations. Other bundled packages have not been license-audited in this bounded
review. The MIT notice must be retained. LGPL distribution obligations require
separate compliance work; inspecting a license is not a compliance certification.
Software library licenses grant no inferred rights to OEM ODX/PDX or other
manufacturer data.

The UI presents separate counts: reference links, catalog integrations verified,
bundled licenses inspected, and software checks passed. The check label includes
its narrow dependency-loading scope. Missing audit evidence supplies no positive
count.

Reproduce from the workspace root:

```bash
GITM_STATE=/tmp/source-tests \
PYTHONPATH=ui-work/diag-integration:source/GearDiag-Raw-Build/app:runtime \
QT_QPA_PLATFORM=offscreen \
python3 -m unittest discover -s ui-work/diag-integration/tests -p test_resources_ui.py
```

Result at audit creation: 12 tests passed. The manifest test recomputes each
recorded evidence-file hash, checks 35 original false catalog flags, and keeps the
software/license counts independent. The dependency test calls the real
`odx_engine.library()` and verifies the bundled version and callable loader.

For the import scan, parse every sorted `app/*.py` file with `ast.parse`, walk
`ast.Import` and `ast.ImportFrom`, and compare each top-level module name with
`can`, `isotp`, `udsoncan`, `doipclient`, and `odxtools`. The manifest records the
scanned file list and matches: only `odxtools` in `odx_engine.py` matched.

The hashed transport evidence is the raw build `app/transport.py`, before
`install.py` applies `patch_transport` for connection-generation isolation.
It identifies the audited source; it does not certify the installed patched
transport. Exact runtime environment, commands, exit codes and dependency-load
output are recorded in the manifest. The full suite also passed:
`GITM_DIAGNOSTIC_TESTS_PASS|134` (134 tests, no skips).
