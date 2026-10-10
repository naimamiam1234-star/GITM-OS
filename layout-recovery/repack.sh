#!/usr/bin/env bash
set -Eeuo pipefail
project=$(pwd)
work=$(mktemp -d /var/tmp/gitm-layout.XXXXXX)
root="$work/root"
iso="$work/iso"
old="$project/dist/GITM-OS-3.3.0-integration-amd64.iso"
(cd dist && sha256sum -c GITM-OS-3.3.0-integration-amd64.iso.sha256)
xorriso -osirrox on -indev "$old" -extract / "$iso"
unsquashfs -processors 2 -d "$root" "$iso/casper/filesystem.squashfs"
cp layout-recovery/gallery_runner.py "$root/opt/gitm/gallery_runner.py"
cp layout-recovery/gallery_native.py "$root/opt/gitm/gallery_native.py"
chroot "$root" /opt/gitm-venv/bin/python -m py_compile /opt/gitm/gallery_runner.py /opt/gitm/gallery_native.py
rm -f "$iso/casper/filesystem.squashfs"
mksquashfs "$root" "$iso/casper/filesystem.squashfs" -noappend -comp zstd -Xcompression-level 8 -processors 2
du -sx --block-size=1 "$root" | cut -f1 > "$iso/casper/filesystem.size"
rm -f "$iso/boot.catalog" "$iso/efi.img"
grub-mkrescue -o "$old" "$iso" -- -volid GITM_OS_33
(cd dist && sha256sum GITM-OS-3.3.0-integration-amd64.iso > GITM-OS-3.3.0-integration-amd64.iso.sha256)
rm -f dist/bios* dist/uefi* dist/gallery.png dist/gallery-serial.log
