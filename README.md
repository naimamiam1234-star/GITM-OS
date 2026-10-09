# GITM OS 3.2 development

Ubuntu 24.04 amd64 desktop foundation with KDE Plasma and real Linux network,
Bluetooth, power, audio, file, document, media and calculator tools.

This repository is a new foundation, not the previously distributed Debian ISO.
AutoDiag, custom Qt shell, workshop records, cloud assistant, graphical installer,
and signed whole-system USB updates are NOT integrated or verified yet.
Do not describe this development image as the complete product.

## Build

Use the **Build GITM development ISO** GitHub Actions workflow. It also starts
when build files change on main. The artifact contains one ISO, SHA-256,
package versions and boot-layout information. Download within two days.
Local builds require Ubuntu with sudo, chroot and mount privileges:

```sh
sudo bash scripts/build-iso.sh
```

Generated boot entries target BIOS and amd64 UEFI. Their presence is not a
runtime boot test. Secure Boot is not claimed. Try only in a virtual machine
until actual boot tests pass. No disk installer is supplied in this foundation.

## Credentials

No provider tokens or update signing private keys may be committed or embedded
in an ISO. Cloudflare is the intended authenticated API gateway. The original
update public key must remain trusted until a validated key rotation procedure
exists; never replace it simply to accept a test update.

## Next acceptance gates

1. BIOS and UEFI boot to usable graphical session.
2. Recover and audit the existing AutoDiag source before public redistribution.
3. Native GITM theme, shell, multilingual first-run and installation flow.
4. Authenticated cloud routes and provider tests without exposing secrets.
5. Signed application and complete-system updates, persistence and rollback tests.
6. Real adapter/ECU coverage verification; no simulated results presented as scans.
