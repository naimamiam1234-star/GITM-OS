# Installer startup probe

Copy `probe.yml` to `.github/workflows/installer-probe.yml`; retain the scripts at their current repository paths. Dispatch the workflow against source run 38190430931. The artifact download action fetches the named ISO artifact without rebuilding it.

The probe extracts the original kernel/initramfs and appends a compressed cpio with a casper-bottom hook. It leaves the ISO and squashfs unchanged, adding only a diagnostic service to the transient live root. QEMU receives only the original ISO and a freshly created 40 GiB qcow2; no host block device or shared folder is attached. It never clicks Next, Install, or any wizard control. `qemu-img compare` checks that virtual disk logical content remains equal to the blank baseline.

The normal test executes the original `/usr/local/bin/gitm-install` as the live user with the Plasma process environment. The separate root test executes documented `calamares --debug` from the service working directory `/`, retaining display authentication. `--debug` is documented in upstream Calamares v3.3.14 `src/calamares/main.cpp`, fetched before authoring. The actual guest `--help` and package version are captured, so compatibility must be checked against the artifact's installed version.

Actual early exit is labeled `actual-exit`; a still-running process is labeled `alive-at-50s` followed by `terminated-by-probe`. Do not misreport a probe termination as a launch failure. pkexec 126 cancellation and 127 authorization failure must not be conflated with Calamares exit 1.

Evidence includes launch stdout/stderr, Calamares session caches, config and modules, package versions, display variables, journal, processes, virtual disk inventory, original ISO digest, QEMU arguments, and screenshots of both launch attempts. The serial transport contains a base64 gzip tar archive. No external credentials are added to the guest.

Limitations: BIOS with direct kernel/initramfs startup only; X11 Plasma expected; no authorization dialog interaction; no completed disk installation or installed-system boot; no UEFI installer verification. A screenshot may capture an authorization prompt, and a process alive at 50 seconds alone does not prove a healthy wizard. Inspect screenshots and logs before proposing a fix. The temporary service is not a production installer modification.
