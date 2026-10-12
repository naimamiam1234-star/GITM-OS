#!/usr/bin/env bash
set -Eeuo pipefail
project=$(pwd)
work=$(mktemp -d /var/tmp/gitm-repair.XXXXXX)
root="$work/root"
iso="$work/iso"
cleanup() { for t in dev/pts dev proc sys; do mountpoint -q "$root/$t" && umount -l "$root/$t" || true; done; }
trap cleanup EXIT
old=$(find "$project/dist" -maxdepth 1 -name '*.iso' -print -quit)
xorriso -osirrox on -indev "$old" -extract / "$iso"
unsquashfs -processors 2 -d "$root" "$iso/casper/filesystem.squashfs"
python3 recovery/patch-casper.py "$root"
install -D -m755 recovery/99gitm-session "$root/usr/share/initramfs-tools/scripts/casper-bottom/99gitm-session"
mount --bind /dev "$root/dev"
mount -t devpts devpts "$root/dev/pts"
mount -t proc proc "$root/proc"
mount -t sysfs sysfs "$root/sys"
chroot "$root" update-initramfs -u -k all
python3 scripts/check-initramfs.py "$root/boot"
cp "$(find "$root/boot" -name 'initrd.img-*' | sort -V | tail -1)" "$iso/casper/initrd"
cleanup
rm -f "$iso/casper/filesystem.squashfs"
mksquashfs "$root" "$iso/casper/filesystem.squashfs" -noappend -comp zstd -Xcompression-level 8 -processors 2
du -sx --block-size=1 "$root" | cut -f1 > "$iso/casper/filesystem.size"
rm -f "$iso/boot.catalog" "$iso/efi.img"
grub-mkrescue -o "$project/dist/GITM-OS-3.3.0-integration-amd64.iso" "$iso" -- -volid GITM_OS_33
cd "$project/dist"
sha256sum GITM-OS-3.3.0-integration-amd64.iso > GITM-OS-3.3.0-integration-amd64.iso.sha256
rm -f bios* uefi*
