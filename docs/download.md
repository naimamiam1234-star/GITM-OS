# Download GITM OS 3.3

Boot-tested connectivity/control-center correction, Ubuntu 24.04 amd64. Actual BIOS and UEFI guest desktops passed in [run 38006827522](https://github.com/naimamiam1234-star/GITM-OS/actions/runs/38006827522).

## One ISO file

[Download GITM-OS-3.3.0-integration-amd64.iso](https://gitm-os-download-33.naimamiam1234.workers.dev/GITM-OS-3.3.0-integration-amd64.iso)

Size: 3008573440 bytes. SHA-256:

```text
c39399eed36a7f6dff97e48140a096567ba75dce819b1e8a5a418bbb224fc7c8
```

The streaming service joins the two immutable release parts without modifying their bytes. It supports single byte ranges and resumed downloads. Download-service verification is recorded in [Actions](https://github.com/naimamiam1234-star/GITM-OS/actions/workflows/download-check.yml).

## Permanent GitHub backup

[Release files](https://github.com/naimamiam1234-star/GITM-OS/releases/tag/gitm-os-3.3.0-statusfix1): download both `.iso.part-01` and `.iso.part-02`, `Join-ISO-Windows.cmd`, and the SHA-256 file into one folder. On Windows run the join script; it checks the complete ISO hash. On Linux:

```sh
cat GITM-OS-3.3.0-integration-amd64.iso.part-01 GITM-OS-3.3.0-integration-amd64.iso.part-02 > GITM-OS-3.3.0-integration-amd64.iso
sha256sum -c GITM-OS-3.3.0-integration-amd64.iso.sha256
```

The parts alone are not bootable. Use the joined ISO for your VM or USB image writer.

## Verification scope

BIOS/UEFI live boot, Qt rendering and split-workspace checks passed. Disk installation, Secure Boot, physical adapters, authenticated provider responses and whole-system rollback remain unverified. Advanced OEM functions are gated/reference functions pending hardware, definitions and vehicle validation; see [coverage](feature-coverage.md). Application updates preserve the original public trust key; future signed bundles still require the corresponding authorized signer.
