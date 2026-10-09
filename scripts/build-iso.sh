#!/usr/bin/env bash
set -Eeuo pipefail
[[ $EUID == 0 ]] || { echo 'Run with sudo on an Ubuntu build host'; exit 1; }
project=$(cd "$(dirname "$0")/.." && pwd)
work=$(mktemp -d /var/tmp/gitm-build.XXXXXX)
root="$work/root"
iso="$work/iso"
cleanup() {
  for target in dev/pts dev proc sys; do mountpoint -q "$root/$target" && umount -l "$root/$target" || true; done
}
trap cleanup EXIT
chroot / /bin/true
apt-get update
apt-get install -y debootstrap squashfs-tools xorriso grub-pc-bin grub-efi-amd64-bin mtools dosfstools
mkdir -p "$iso/casper" "$iso/boot/grub" "$project/dist"
debootstrap --arch=amd64 --variant=minbase noble "$root" http://archive.ubuntu.com/ubuntu/
cat > "$root/etc/apt/sources.list" <<'SOURCES'
deb http://archive.ubuntu.com/ubuntu noble main restricted universe multiverse
deb http://archive.ubuntu.com/ubuntu noble-updates main restricted universe multiverse
deb http://security.ubuntu.com/ubuntu noble-security main restricted universe multiverse
SOURCES
cp /etc/resolv.conf "$root/etc/resolv.conf"
mount --bind /dev "$root/dev"
mount -t devpts devpts "$root/dev/pts"
mount -t proc proc "$root/proc"
mount -t sysfs sysfs "$root/sys"
printf '#!/bin/sh\nexit 101\n' > "$root/usr/sbin/policy-rc.d"
chmod 755 "$root/usr/sbin/policy-rc.d"
chroot "$root" /usr/bin/env DEBIAN_FRONTEND=noninteractive /bin/bash <<'ROOT'
set -Eeuo pipefail
apt-get update
apt-get install -y linux-generic casper initramfs-tools dbus systemd-sysv sudo locales plasma-desktop sddm xserver-xorg network-manager plasma-nm bluez bluedevil pipewire wireplumber upower power-profiles-daemon polkit-kde-agent-1 dolphin konsole okular kate kde-config-screenlocker kde-config-gtk-style fonts-noto-core fonts-noto-color-emoji qt6-declarative-dev python3-pyqt6 python3-venv v4l-utils vlc qalculate-qt falkon
locale-gen en_US.UTF-8 fr_FR.UTF-8 ar_MA.UTF-8
printf 'LANG=en_US.UTF-8\n' > /etc/default/locale
printf 'gitm\n' > /etc/hostname
printf '127.0.0.1 localhost\n127.0.1.1 gitm\n' > /etc/hosts
mkdir -p /etc/casper.conf.d
cat > /etc/casper.conf <<'CASPER'
export USERNAME="gitm"
export USERFULLNAME="GITM Live User"
export HOST="gitm"
CASPER
systemctl enable NetworkManager sddm
systemctl set-default graphical.target
update-initramfs -u -k all
apt-get clean
rm /usr/sbin/policy-rc.d
ROOT
# Preserve upstream identification and notices. Product identity is separate.
mkdir -p "$root/etc/gitm"
printf '{"product":"GITM OS","version":"3.2.0-development","base":"Ubuntu 24.04","stage":"desktop-foundation","autodiag_integrated":false,"full_system_update_verified":false}\n' > "$root/etc/gitm/release.json"
chroot "$root" dpkg-query -W --showformat='${Package} ${Version}\n' > "$iso/casper/filesystem.manifest"
cp "$(find "$root/boot" -name 'vmlinuz-*' | sort -V | tail -1)" "$iso/casper/vmlinuz"
cp "$(find "$root/boot" -name 'initrd.img-*' | sort -V | tail -1)" "$iso/casper/initrd"
cleanup
truncate -s 0 "$root/etc/machine-id"
rm -f "$root/var/lib/dbus/machine-id"
rm -rf "$root/var/lib/apt/lists/"*
du -sx --block-size=1 "$root" | cut -f1 > "$iso/casper/filesystem.size"
mksquashfs "$root" "$iso/casper/filesystem.squashfs" -noappend -comp xz -processors 2
cat > "$iso/boot/grub/grub.cfg" <<'GRUB'
set timeout=8
set default=0
menuentry 'GITM OS 3.2 — Development desktop' {
 linux /casper/vmlinuz boot=casper quiet ---
 initrd /casper/initrd
}
menuentry 'GITM OS — Safe graphics' {
 linux /casper/vmlinuz boot=casper nomodeset ---
 initrd /casper/initrd
}
GRUB
grub-mkrescue -o "$project/dist/GITM-OS-3.2.0-development-amd64.iso" "$iso" -- -volid GITM_OS_32
cd "$project/dist"
sha256sum GITM-OS-3.2.0-development-amd64.iso > GITM-OS-3.2.0-development-amd64.iso.sha256
xorriso -indev GITM-OS-3.2.0-development-amd64.iso -report_el_torito plain > boot-layout.txt 2>&1
cp "$iso/casper/filesystem.manifest" packages.txt
printf 'Built development image; runtime boot, installation, AutoDiag, and updates are not verified.\n' > STATUS.txt
