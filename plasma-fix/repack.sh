#!/bin/bash
set -Eeuo pipefail
project=$PWD
apt-get update
apt-get install -y squashfs-tools xorriso grub-pc-bin grub-efi-amd64-bin mtools qemu-system-x86 ovmf python3-pil
work=$(mktemp -d /var/tmp/gitm-plasma-fix.XXXXXX)
source=$(find input -name '*.iso' -print -quit)
xorriso -osirrox on -indev "$source" -extract /casper/filesystem.squashfs "$work/original.squashfs"
unsquashfs -d "$work/root" "$work/original.squashfs"
install -D -m644 overlay/etc/calamares/branding/gitm/branding.desc "$work/root/etc/calamares/branding/gitm/branding.desc"
install -D -m644 overlay/etc/calamares/settings.conf "$work/root/etc/calamares/settings.conf"
for config in partition welcome mount gitm-target-check gitm-initramfs; do
  install -D -m644 "overlay/etc/calamares/modules/$config.conf" "$work/root/etc/calamares/modules/$config.conf"
done
install -m755 plasma-fix/gitm-desktop "$work/root/usr/local/bin/gitm-desktop"
install -D -m600 plasma-fix/network-manager.yaml "$work/root/etc/netplan/01-gitm-network-manager.yaml"
install -m755 plasma-fix/network-smoke.py "$work/root/usr/local/bin/gitm-network-smoke"
install -m644 plasma-fix/network-smoke.service "$work/root/etc/systemd/system/gitm-network-smoke.service"
ln -sf /etc/systemd/system/gitm-network-smoke.service "$work/root/etc/systemd/system/multi-user.target.wants/gitm-network-smoke.service"
sed -i '/^#!\/bin\/sh/a export QT_STYLE_OVERRIDE=Fusion\nexport QT_QPA_PLATFORMTHEME=generic' "$work/root/usr/local/bin/gitm-autodiag"
# Use the application's bundled style only for Python Qt, not native programs.
python3 - "$work/root/opt/gitm/gitm_desktop.py" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]);s=p.read_text()
s=s.replace('p=QProcess(self);p.setProgram(argv[0]);', "p=QProcess(self)\n  from PySide6.QtCore import QProcessEnvironment\n  env=QProcessEnvironment.systemEnvironment()\n  if argv[0]!=sys.executable:\n   env.remove('QT_STYLE_OVERRIDE');env.remove('QT_QPA_PLATFORMTHEME')\n  p.setProcessEnvironment(env);p.setProgram(argv[0]);")
p.write_text(s)
PY
bash theme-integration/install-root.sh "$work/root"
# Populate APT's AppStream catalogue after all desktop packages are installed.
# Preserve these lists in the live image so Discover works on first launch.
chroot "$work/root" apt-get update
chroot "$work/root" env DEBIAN_FRONTEND=noninteractive apt-get install -y console-setup
# Calamares uses ckbcomp to show real key labels in its keyboard preview.
chroot "$work/root" ckbcomp us >/dev/null
chroot "$work/root" appstreamcli refresh-cache --force
chroot "$work/root" env LC_ALL=C appstreamcli status | python3 plasma-fix/check-catalog.py
mksquashfs "$work/root" "$work/fixed.squashfs" -noappend -comp zstd -Xcompression-level 8 -processors 2
mkdir -p dist
xorriso -osirrox on -indev "$source" -extract / "$work/iso"
mv "$work/fixed.squashfs" "$work/iso/casper/filesystem.squashfs"
rm -f "$work/iso/boot.catalog"
grub-mkrescue -o dist/GITM-OS-3.3.0-integration-amd64.iso "$work/iso" -- -volid GITM_OS_33
for evidence in input/*.txt; do
  [[ $(basename "$evidence") == diagnostic-tests.txt ]] || cp "$evidence" dist/
done
chroot "$work/root" dpkg-query -W -f='${binary:Package} ${Version}\n' > dist/packages.txt
cd dist
sha256sum GITM-OS-3.3.0-integration-amd64.iso > GITM-OS-3.3.0-integration-amd64.iso.sha256
