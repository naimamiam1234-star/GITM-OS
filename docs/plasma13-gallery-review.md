# Plasma13 gallery review — 69 actual pre-install-fix captures

Reviewed 2026-10-12. Repository `naimamiam1234-star/GITM-OS`, source13CI run `38248858347`, head `c7b3440026d30e61db2d9f0d5c80ab14fade0694`, gallery artifact `11748063829`.

**Scope:** exactly 69 original PNG screenshots, safely extracted from the actual CI artifact. Every image was visually inspected on six contact sheets; `app-install`, `autodiag-02`, `diag-bench-live`, and `autodiag-16` were additionally inspected at full resolution. This is pre-install-fix review evidence, not a final release, not a 70-image final gallery, and not proof of a completed installation.

Evidence folder: https://drive.google.com/drive/folders/1DEXcSeqtLDREI58Itb52h98JYwNKSA_B

## Visible results

- Native Plasma desktop, dark/light modes, settings, Dolphin, Firefox, KCalc, Okular, Gwenview, VLC, Bluetooth manager, network manager, virtual keyboard, power controls, volume controls, and Discover open in actual captures. Discover shows populated application cards. VM screenshots cannot establish physical Wi-Fi, Bluetooth, camera, battery, CAN/VCI or audio hardware operation.
- AutoDiag brand selection shows readable manufacturer labels with neutral gray backplates around logo images. The visible backplates are consistent with the expected 32×24 tile footprint; screenshots alone do not certify the source dimensions. Grid rows extend below the viewport with a scrollbar.
- `diag-bench-live.png` explicitly identifies a simulator session. Selected ECU 7E8, PID 0C, engine speed is a flat 1726 rpm line. Minimum/mean/maximum are all 1726. The five Y ticks are 1812.3, 1769.2, 1726, 1682.8, 1639.7. X ticks show actual elapsed seconds 0, 0.9986, 1.997, 2.996, 3.994; the trace is centered in the scale.
- `autodiag-16.png` source catalog clearly displays 35 reference links, 0 verified source integrations, 2 loaded-library licenses, and 1 successful software check. Text distinguishes a sample ODX load from a vehicle test, library licenses from manufacturer data, and local/reference presence from integration or redistribution rights.
- Simulator DTC, freeze-frame, readiness, report, and summary captures are present; the report visibly labels simulation and disclaims a physical-vehicle test. The expected 137-test run is external CI/test evidence, not information proved by these screenshots.

## Issues and release limits

1. **Installer blocks at Welcome.** `app-install.png` opens the actual GITM OS Installer but says “There are no partitions to install on.” Next is disabled. The CI VM had no install disk; this gallery provides no partitioning, disk installation, or installed-system boot proof. A disposable disk and full installer smoke test are required in the subsequent fixed build.
2. The installer remains behind audio, Bluetooth manager, network, keyboard and some later native-app captures. They prove the foreground app opened, but retain the earlier blocking error and are less clean as a final screenshot gallery.
3. AutoDiag has a narrow visible left scrollbar/gutter across several views. The source-detail pane clips its lower redistribution text until scrolled; catalog status strings truncate with ellipses. These are layout/presentation issues rather than evidence of successful integrations.
4. Several settings capture names share similar broad settings landing pages. Search/sync/power captures show controls, but still images cannot prove their actions completed. Firefox and VLC show first-run welcome/privacy dialogs. Hardware-unavailable views accurately describe VM limitations and should remain described as such.

Original evidence is preserved; older Qt-Local-48 and Plasma12 review folders were not moved, renamed, overwritten, or deleted. `manifest.json` accompanies the originals with exact names, byte counts and SHA-256 hashes. Contact sheets are local inspection aids and are not counted as original captures.
