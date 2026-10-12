# Disposable installer validation

`prepare.sh ISO OUTPUT disk` adds an ephemeral test service to a copy of the original initramfs. The ISO and squashfs remain unchanged. The guest first requires all shipped Calamares configuration files to equal the checked-out files; only a completion sentinel is then added to the transient live root.

`boot-install.py ISO --output-root OUTPUT` creates a fresh 40 GiB virtual disk tagged GITM-CI-ONLY. It refuses existing fixtures, verifies the guest disk identity and blankness, checks the root partition plan, performs installation and requires the final post-unmount sentinel. It then boots the installed disk without ISO, external kernel or initramfs, requires its root partition and native Plasma session, and opens AutoDiag as the non-root GUI user.

Use `--uefi` for OVMF with fresh NVRAM preserved between installation and disk boot. The publisher tests both firmware modes against the exact final ISO before release. Logs, screenshots, source digest and guest archives are retained; virtual disks are not uploaded. The direct-kernel live test does not test the ISO firmware bootloader or Secure Boot; the source build's native ISO boot checks provide the separate boot evidence.

The default prepare mode retains the older non-destructive startup probe through guest-probe.py. These helpers are CI-only and are never installed in the production ISO. Do not connect host block devices or shared folders.
