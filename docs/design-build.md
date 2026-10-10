# GITM OS 3.3 — Design update 1
Ubuntu-based GITM desktop with independent AutoDiag.
Changes: persistent light/dark appearance, reduced-motion and performance settings, searchable native settings launchers, Esc to dismiss the control panel, Ctrl+F to focus application search. Existing ten-app layout, square RAM/storage panel, state-aware radio/battery icons and hidden control panel are preserved.
The browser namespace policy is loaded by a dedicated systemd unit before SDDM, including Casper Live boots. No global AppArmor restrictions or Chromium sandbox are disabled.
Release publication requires actual BIOS/UEFI boot, a real Falkon window under its named policy, sixty freshly captured guest screens and nonblank-image checks. Guest capture-only mode is not enabled in normal boot menus.
These are real desktop changes, not a QML/KWin migration, complete notification service, universal OEM capability or device certification. AutoDiag's compatibility checks remain in place. The installer was opened to its authorization prompt; no disk installation or vehicle mutations were performed.
Download both ISO parts and Join-ISO-Windows.cmd into one folder on Windows, run the command file to assemble and SHA256-check the ISO. For Linux use cat *.part-01 *.part-02 > GITM-OS-3.3.0-integration-amd64.iso and sha256sum -c the supplied checksum. Existing parts from a previous release must not be mixed.
Reference: https://ubuntu.com/blog/ubuntu-23-10-restricted-unprivileged-user-namespaces
