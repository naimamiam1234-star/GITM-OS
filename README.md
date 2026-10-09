# GITM OS 3.3 integration

Ubuntu 24.04 amd64 live system with the GITM Qt desktop, Openbox window management,
KDE system utilities, and native GITM AutoDiag. The general desktop is the startup
screen; automotive functions remain inside AutoDiag.

Included: file manager, browser, terminal, PDF/photo/media tools, calculator,
network/Bluetooth/audio/display tools, graphical disk installer, Ubuntu package
updates, signed AutoDiag application updates and rollback, workshop records,
customer invoices, diagnostic definition import, OBD reads/live data, read-only
ECU discovery, CAN tools and authenticated Cloudflare assistant UI. Split Screen
shows faults and measured data; a second diagnostic process supports manual pairing
of a separate adapter. Adapter reservations prevent two sessions sharing a target.

The source is recovered from the pinned Drive snapshot, with its checksum and
upstream attribution. The wallpaper is downloaded from a versioned Cloudinary URL
and verified before inclusion. These services are not required to use the desktop
once the ISO is built. Cloud features require internet and user sign-in.

## Build and download

Use **Build GITM development ISO** under GitHub Actions. The ISO artifact contains
one bootable ISO, SHA-256, package inventories and boot reports. Boot screenshots
and logs also have a separate small artifact. Artifacts are retained for 14 days.
Local builds require Ubuntu root, chroot and mount capabilities:

```sh
sudo bash scripts/build-iso.sh
sudo python3 scripts/boot-smoke.py
```

The workflow verifies source patching, Qt rendering and actual BIOS/UEFI guest
boot. A successful build is not proof of installation on physical hardware,
Secure Boot, or vehicle compatibility. Consult the run result and boot screenshots.
Calamares installation must be validated independently before installing on a
computer containing important data.

## Updates

Ubuntu packages use Plasma Discover/Ubuntu repositories. AutoDiag accepts signed
`.gitmupdate` bundles and retains the original public trust key. The launcher
selects the installed release or its rollback; customer records stay in the user
state directory. This is not a signed whole-OS image/bootloader update service.
Live changes need persistent storage or an installed system to survive reboot.
Signing private keys and cloud provider secrets are not included in the ISO.

## Actual vehicle support

OBD decoding and adapter transport paths are implemented, but vehicle results must
be checked on the actual adapter and vehicle. The imported datasets provide
reference information, not universal executable vehicle coverage. ECU coding,
active tests, 41 universal service procedures, TPMS programming, ADAS calibration,
key programming and EV-specific procedures are not certified or fully implemented.
They require exact ECU definitions, compatible hardware and documented testing.
Unavailable functions remain labeled; simulated values are never shown as scans.

See [feature coverage](docs/feature-coverage.md) for the acceptance matrix.
