#!/bin/bash
set -Eeuo pipefail
project=$PWD
apt-get update
apt-get install -y squashfs-tools xorriso grub-pc-bin grub-efi-amd64-bin mtools qemu-system-x86 ovmf python3-pil
work=$(mktemp -d /var/tmp/gitm-plasma-fix.XXXXXX)
source=$(find input -name '*.iso' -print -quit)
xorriso -osirrox on -indev "$source" -extract /casper/filesystem.squashfs "$work/original.squashfs"
unsquashfs -d "$work/root" "$work/original.squashfs"
install -m755 plasma-fix/gitm-desktop "$work/root/usr/local/bin/gitm-desktop"
sed -i '/^#!\/bin\/sh/a export QT_STYLE_OVERRIDE=Fusion\nexport QT_QPA_PLATFORMTHEME=generic' "$work/root/usr/local/bin/gitm-autodiag"
# Use the application's bundled style only for Python Qt, not native programs.
python3 - "$work/root/opt/gitm/gitm_desktop.py" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]);s=p.read_text()
s=s.replace('p=QProcess(self);p.setProgram(argv[0]);', "p=QProcess(self)\n  from PySide6.QtCore import QProcessEnvironment\n  env=QProcessEnvironment.systemEnvironment()\n  if argv[0]!=sys.executable:\n   env.remove('QT_STYLE_OVERRIDE');env.remove('QT_QPA_PLATFORMTHEME')\n  p.setProcessEnvironment(env);p.setProgram(argv[0]);")
p.write_text(s)
PY
mksquashfs "$work/root" "$work/fixed.squashfs" -noappend -comp zstd -Xcompression-level 8 -processors 2
mkdir -p dist
xorriso -osirrox on -indev "$source" -extract / "$work/iso"
mv "$work/fixed.squashfs" "$work/iso/casper/filesystem.squashfs"
rm -f "$work/iso/boot.catalog"
grub-mkrescue -o dist/GITM-OS-3.3.0-integration-amd64.iso "$work/iso" -- -volid GITM_OS_33
cp input/*.txt dist/
cd dist
sha256sum GITM-OS-3.3.0-integration-amd64.iso > GITM-OS-3.3.0-integration-amd64.iso.sha256
