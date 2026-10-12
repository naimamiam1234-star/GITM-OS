#!/bin/bash
set -Eeuo pipefail
source=${1:?source ISO required}; dest=${2:-dist/install-probe}; mode=${3:-startup}
base=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$dest"
sha256sum "$source" > "$dest/source-iso.sha256"
xorriso -osirrox on -indev "$source" -extract /casper/vmlinuz "$dest/vmlinuz" -extract /casper/initrd "$dest/initrd.original"
helper="$base/guest-probe.py"
if [[ "$mode" == disk ]]; then
  helper="$dest/guest-install-embedded.py"
  python3 - "$base" "$helper" <<'PY'
import json,pathlib,sys
base=pathlib.Path(sys.argv[1]); overlay=base.parent/'overlay/etc/calamares'
config={str(p.relative_to(overlay)):p.read_text() for p in overlay.rglob('*.conf')}
text=(base/'guest-install.py').read_text().replace('CONFIG = {} # replaced by prepare.sh in the test-only helper copy','CONFIG = '+repr(config))
pathlib.Path(sys.argv[2]).write_text(text)
PY
fi
python3 "$base/inject-initrd.py" "$dest/initrd.original" "$dest/initrd" --helper "$helper"
