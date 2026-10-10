#!/bin/bash
set -Eeuo pipefail
apt-get update
apt-get install -y squashfs-tools xorriso
work=$(mktemp -d /var/tmp/gitm-catalog.XXXXXX)
source=$(find input -name '*.iso' -print -quit)
xorriso -osirrox on -indev "$source" -extract /casper/filesystem.squashfs "$work/root.squashfs"
unsquashfs -d "$work/root" "$work/root.squashfs" >/dev/null
mkdir -p evidence
for stage in before after; do
  if [ "$stage" = after ]; then
    chroot "$work/root" apt-get update 2>&1 | tee evidence/apt-update.log
    chroot "$work/root" appstreamcli refresh-cache --force 2>&1 | tee evidence/refresh.log
  fi
  {
    echo "GITM_CATALOG_STAGE|$stage"
    chroot "$work/root" appstreamcli status || true
    chroot "$work/root" apt-cache policy kate || true
    chroot "$work/root" appstreamcli search kate --details || true
    for dir in var/lib/apt/lists var/lib/swcatalog var/cache/swcatalog var/lib/app-info var/cache/app-info; do
      if [ -d "$work/root/$dir" ]; then
        echo "GITM_CATALOG_DIRECTORY|$dir"
        find "$work/root/$dir" -maxdepth 2 -type f -printf '%f %s bytes\n' | head -40 || true
      fi
    done
  } 2>&1 | tee "evidence/$stage.log"
done
