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
cp browser-recovery/gallery_runner.py "$root/opt/gitm/gallery_runner.py"
cp layout-recovery/gallery_native.py "$root/opt/gitm/gallery_native.py"
cp browser-recovery/gitm_desktop.py "$root/opt/gitm/gitm_desktop.py"
cp browser-recovery/desktop_radios.py "$root/opt/gitm/desktop_radios.py"
install -D -m644 browser-recovery/gitm-falkon "$root/etc/apparmor.d/gitm-falkon"
install -D -m644 browser-recovery/gitm-browser-policy.service "$root/etc/systemd/system/gitm-browser-policy.service"
chroot "$root" systemctl enable gitm-browser-policy.service
chroot "$root" apparmor_parser -Q -T /etc/apparmor.d/gitm-falkon
chroot "$root" /opt/gitm-venv/bin/python -m py_compile /opt/gitm/gitm_desktop.py /opt/gitm/gallery_runner.py /opt/gitm/gallery_native.py
mkdir -p "$root/var/tmp/gitm-ui-check"
cp scripts/check-status.py "$root/var/tmp/gitm-ui-check/check-status.py"
cp browser-recovery/check-appearance.py "$root/var/tmp/gitm-ui-check/check-appearance.py"
chroot "$root" env PYTHONPATH=/opt/gitm QT_QPA_PLATFORM=offscreen GITM_STATE=/var/tmp/gitm-validation /opt/gitm-venv/bin/python /var/tmp/gitm-ui-check/check-appearance.py
rm -rf "$root/var/tmp/gitm-validation" "$root/var/tmp/gitm-ui-check"
rm -f "$iso/casper/filesystem.squashfs"
mksquashfs "$root" "$iso/casper/filesystem.squashfs" -noappend -comp zstd -Xcompression-level 8 -processors 2
du -sx --block-size=1 "$root" | cut -f1 > "$iso/casper/filesystem.size"
rm -f "$iso/boot.catalog" "$iso/efi.img"
grub-mkrescue -o "$old" "$iso" -- -volid GITM_OS_33
(cd dist && sha256sum GITM-OS-3.3.0-integration-amd64.iso > GITM-OS-3.3.0-integration-amd64.iso.sha256)
rm -f dist/bios* dist/uefi* dist/gallery.png dist/gallery-serial.log

