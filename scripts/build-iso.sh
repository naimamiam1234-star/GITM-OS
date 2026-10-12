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
apt-get install -y debootstrap squashfs-tools xorriso grub-pc-bin grub-efi-amd64-bin mtools dosfstools qemu-system-x86 ovmf python3-pil
cd "$project"
python3 scripts/fetch-source.py
python3 scripts/patch-source.py
python3 scripts/fetch-wallpaper.py
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
apt-get install -y linux-generic linux-firmware openbox wmctrl blueman casper initramfs-tools dbus systemd-sysv sudo locales plasma-desktop sddm xserver-xorg network-manager plasma-nm bluez bluedevil pipewire wireplumber upower power-profiles-daemon polkit-kde-agent-1 dolphin konsole okular kate kde-config-screenlocker kde-config-gtk-style fonts-noto-core fonts-noto-color-emoji qt6-declarative-dev python3-pyqt6 python3-venv v4l-utils vlc kcalc falkon gwenview plasma-systemmonitor plasma-discover packagekit software-properties-qt system-config-printer gufw gnome-disk-utility kscreen kde-config-gtk-style pavucontrol onboard network-manager-gnome rfkill can-utils libxcb-cursor0 libxkbcommon-x11-0 libegl1 libopengl0 libpulse0 libnss3 calamares grub-pc-bin grub-efi-amd64-bin efibootmgr rsync btrfs-progs dosfstools partitionmanager gparted openssl python3-pip python3-serial language-pack-ar language-pack-fr
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
mkdir -p /etc/systemd/journald.conf.d
printf "[Journal]\nForwardToConsole=yes\nTTYPath=/dev/ttyS0\nMaxLevelConsole=info\n" > /etc/systemd/journald.conf.d/gitm-test-console.conf
printf 'overlay\nsquashfs\nloop\nisofs\n' >> /etc/initramfs-tools/modules
update-initramfs -u -k all
apt-get clean
rm /usr/sbin/policy-rc.d
ROOT
cp -a "$project/build-input/app" "$root/opt/gitm"
cp -a "$project/overlay/." "$root/"
install -D "$project/build-input/overlay/usr/share/gitm/update-public.pem" "$root/usr/share/gitm/update-public.pem"
chmod 755 "$root/usr/local/bin/gitm-session" "$root/usr/local/bin/gitm-autodiag" "$root/usr/local/bin/gitm-install" "$root/usr/local/sbin/gitm-device-admin"
chroot "$root" python3 -m venv /opt/gitm-venv
chroot "$root" /opt/gitm-venv/bin/pip install PySide6==6.8.3 bleak==0.22.3 odxtools==11.6.2 python-can can-isotp udsoncan doipclient requests pyserial
chroot "$root" /opt/gitm-venv/bin/pip freeze > "$project/dist/python-packages.txt"
chroot "$root" /usr/bin/env QT_QPA_PLATFORM=offscreen GITM_STATE=/tmp/gitm-smoke GITM_SCREENSHOT=/tmp/gitm-native.png /opt/gitm-venv/bin/python /opt/gitm/native.py --smoke
cp "$root/tmp/gitm-native.png" "$project/dist/qt-smoke.png"
cp "$project/scripts/check-split.py" "$root/tmp/check-split.py"
mkdir -p "$root/build-input" "$root/dist"
ln -s /opt/gitm "$root/build-input/app"
chroot "$root" /usr/bin/env QT_QPA_PLATFORM=offscreen GITM_STATE=/tmp/gitm-split-check /opt/gitm-venv/bin/python /tmp/check-split.py
cp "$root/dist/split-smoke.png" "$project/dist/split-smoke.png"
rm -rf "$root/build-input" "$root/dist" "$root/tmp/check-split.py" "$root/tmp/gitm-split-check"
rm -rf "$root/tmp/gitm-smoke" "$root/tmp/gitm-native.png"
chroot "$root" /usr/bin/env QT_QPA_PLATFORM=offscreen GITM_STATE=/tmp/gitm-desktop-smoke GITM_SCREENSHOT=/tmp/gitm-desktop.png /opt/gitm-venv/bin/python /opt/gitm/gitm_desktop.py --smoke
cp "$root/tmp/gitm-desktop.png" "$project/dist/desktop-smoke.png"
rm -rf "$root/tmp/gitm-desktop-smoke" "$root/tmp/gitm-desktop.png"
mkdir -p "$root/var/tmp/gitm-ui-check"
cp "$project/scripts/check-status.py" "$root/var/tmp/gitm-ui-check/check-status.py"
cp "$project/scripts/check-appearance.py" "$root/var/tmp/gitm-ui-check/check-appearance.py"
chroot "$root" env PYTHONPATH=/opt/gitm QT_QPA_PLATFORM=offscreen GITM_STATE=/var/tmp/gitm-validation /opt/gitm-venv/bin/python /var/tmp/gitm-ui-check/check-appearance.py
rm -rf "$root/var/tmp/gitm-validation" "$root/var/tmp/gitm-ui-check"
python3 recovery/patch-casper.py "$root"
install -D -m755 recovery/99gitm-session "$root/usr/share/initramfs-tools/scripts/casper-bottom/99gitm-session"
chroot "$root" update-initramfs -u -k all
python3 scripts/check-initramfs.py "$root/boot"
mkdir -p "$root/etc/gitm"
printf '{"product":"GITM OS","version":"3.3.0-integration","base":"Ubuntu 24.04","autodiag_integrated":true,"full_system_update_verified":false,"installer_verified":false}\n' > "$root/etc/gitm/release.json"
chroot "$root" dpkg-query -W --showformat='${Package} ${Version}\n' > "$iso/casper/filesystem.manifest"
cp "$(find "$root/boot" -name 'vmlinuz-*' | sort -V | tail -1)" "$iso/casper/vmlinuz"
cp "$(find "$root/boot" -name 'initrd.img-*' | sort -V | tail -1)" "$iso/casper/initrd"
cleanup
truncate -s 0 "$root/etc/machine-id"
rm -f "$root/var/lib/dbus/machine-id"
rm -rf "$root/var/lib/apt/lists/"*
du -sx --block-size=1 "$root" | cut -f1 > "$iso/casper/filesystem.size"
mksquashfs "$root" "$iso/casper/filesystem.squashfs" -noappend -comp zstd -Xcompression-level 8 -processors 2
cat > "$iso/boot/grub/grub.cfg" <<'GRUB'
set timeout=8
set default=0
menuentry 'GITM OS 3.3 — Integration Preview' {
 linux /casper/vmlinuz boot=casper console=tty0 console=ttyS0,115200 ---
 initrd /casper/initrd
}
menuentry 'GITM OS — Safe graphics' {
 linux /casper/vmlinuz boot=casper nomodeset console=tty0 console=ttyS0,115200 ---
 initrd /casper/initrd
}
GRUB
grub-mkrescue -o "$project/dist/GITM-OS-3.3.0-integration-amd64.iso" "$iso" -- -volid GITM_OS_33
cd "$project/dist"
sha256sum GITM-OS-3.3.0-integration-amd64.iso > GITM-OS-3.3.0-integration-amd64.iso.sha256
xorriso -indev GITM-OS-3.3.0-integration-amd64.iso -report_el_torito plain > boot-layout.txt 2>&1
cp "$iso/casper/filesystem.manifest" packages.txt
printf 'Built development image; Qt integration smoke passed; actual guest boot results are recorded separately. Installation, vehicle hardware, authenticated cloud, and full-system updates are not verified.\n' > STATUS.txt
