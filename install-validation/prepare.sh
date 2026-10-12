#!/bin/bash
set -Eeuo pipefail
source=${1:?source ISO required}; dest=${2:-dist/install-probe}
mkdir -p "$dest"
sha256sum "$source" > "$dest/source-iso.sha256"
xorriso -osirrox on -indev "$source" -extract /casper/vmlinuz "$dest/vmlinuz" -extract /casper/initrd "$dest/initrd.original"
payload=$(mktemp -d)
trap 'rm -rf "$payload"' EXIT
mkdir -p "$payload/scripts/casper-bottom" "$payload/gitm-probe"
cp install-validation/guest-probe.py "$payload/gitm-probe/guest-probe.py"
cat > "$payload/scripts/casper-bottom/99gitm-installer-probe" <<'HOOK'
#!/bin/sh
PREREQ=""
prereqs() { echo "$PREREQ"; }
case "$1" in prereqs) prereqs; exit 0;; esac
mkdir -p "$rootmnt/usr/local/lib/gitm-probe" "$rootmnt/etc/systemd/system/multi-user.target.wants"
cp /gitm-probe/guest-probe.py "$rootmnt/usr/local/lib/gitm-probe/guest-probe.py"
cat > "$rootmnt/etc/systemd/system/gitm-installer-probe.service" <<'UNIT'
[Unit]
Description=Test-only non-writing installer startup probe
After=display-manager.service
[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /usr/local/lib/gitm-probe/guest-probe.py
TimeoutStartSec=1100
[Install]
WantedBy=multi-user.target
UNIT
ln -sf /etc/systemd/system/gitm-installer-probe.service "$rootmnt/etc/systemd/system/multi-user.target.wants/gitm-installer-probe.service"
HOOK
chmod 755 "$payload/scripts/casper-bottom/99gitm-installer-probe"
cp "$dest/initrd.original" "$dest/initrd"
(cd "$payload"; find . -print0 | cpio --null -o --format=newc 2>/dev/null | gzip -1) >> "$dest/initrd"
