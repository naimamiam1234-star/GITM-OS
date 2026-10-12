#!/usr/bin/env python3
"""Bundle distro VM tools and their runtime dependencies without host mounts."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else 'dist/qemu-runtime').resolve()
if root.exists():
    raise SystemExit('Refusing to overwrite an existing runtime directory')
for directory in ['bin', 'lib', 'modules', 'share', 'wrappers']:
    (root/directory).mkdir(parents=True, exist_ok=True)
names = ['qemu-system-x86_64', 'qemu-img', 'xorriso', 'unsquashfs']
queue = []
origins = {}

def copy(source, target):
    source = Path(source)
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if target.read_bytes() != source.read_bytes():
            raise RuntimeError('Conflicting libraries: '+str(target)+' from '+str(source))
    else:
        shutil.copy2(source, target, follow_symlinks=True)
    origins[str(target.relative_to(root))] = str(source)

for name in names:
    source = shutil.which(name)
    if not source:
        raise SystemExit('Missing required executable: '+name)
    copy(source, root/'bin'/name)
    queue.append(Path(source))

# QEMU dlopens modules which ldd on the main executable cannot discover.
for path in ['/usr/lib/x86_64-linux-gnu/qemu', '/usr/lib/qemu']:
    directory = Path(path)
    if not directory.is_dir():
        continue
    for source in directory.rglob('*.so'):
        copy(source, root/'modules'/source.name)
        queue.append(source)

seen = set()
ldd_reports = {}
while queue:
    source = queue.pop()
    key = str(source.resolve())
    if key in seen:
        continue
    seen.add(key)
    result = subprocess.run(['ldd', str(source)], capture_output=True, text=True)
    report = result.stdout + result.stderr
    ldd_reports[str(source)] = report
    if 'not found' in report:
        raise RuntimeError('Unresolved dependency of '+str(source)+'\n'+report)
    if result.returncode and 'not a dynamic executable' not in report:
        raise RuntimeError('ldd failed for '+str(source)+'\n'+report)
    for dep in re.findall(r'(?:=>\s*)?(/[^\s()]+)', report):
        if not Path(dep).is_file():
            continue
        copy(dep, root/'lib'/Path(dep).name)
        queue.append(Path(dep))

for name in ['qemu', 'seabios', 'OVMF', 'qemu-system-x86']:
    source = Path('/usr/share')/name
    if source.is_dir():
        shutil.copytree(source, root/'share'/name, symlinks=False)
loader = root/'lib'/'ld-linux-x86-64.so.2'
if not loader.exists():
    raise RuntimeError('Missing bundled ELF loader')

for name in names:
    extra = ' -L "$bundle/share/qemu"' if name == 'qemu-system-x86_64' else ''
    script = '''#!/bin/sh
set -eu
bundle=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
export QEMU_MODULE_DIR="$bundle/modules"
exec "$bundle/lib/ld-linux-x86-64.so.2" --library-path "$bundle/lib" "$bundle/bin/NAME"EXTRA "$@"
'''.replace('NAME', name).replace('EXTRA', extra)
    target=root/'wrappers'/name
    target.write_text(script)
    target.chmod(0o755)

(root/'ldd-reports.json').write_text(json.dumps(ldd_reports, indent=2))
(root/'origins.json').write_text(json.dumps(origins, indent=2))
packages=subprocess.run(['dpkg-query','-W','-f=${binary:Package} ${Version}\n'],capture_output=True,text=True,check=True)
(root/'packages.txt').write_text(packages.stdout)
(root/'README.txt').write_text('''Ubuntu 24.04 x86_64 VM runtime. Use wrappers/qemu-system-x86_64,
wrappers/qemu-img, wrappers/xorriso, and wrappers/unsquashfs. The wrappers
explicitly use the bundled ELF loader and libraries, avoiding installation,
root privileges, chroot, or global LD_LIBRARY_PATH modifications.

Firmware: share/qemu for BIOS; share/OVMF for explicit UEFI pflash drives.
QEMU plugins: modules. The main wrapper automatically passes -L share/qemu.
Only regular package files and dependency metadata were copied. No home,
credentials, environment snapshot, package-manager config, or runner workspace
is included.

Example safe TCG launch (create a new image first):
  wrappers/qemu-img create -f qcow2 test-only.qcow2 40G
  wrappers/qemu-system-x86_64 -machine q35,accel=tcg -cpu max -m 6144 -smp 2 \\
    -drive file=test-only.qcow2,format=qcow2,if=virtio -cdrom SOURCE.iso \\
    -display none -serial file:serial.log -monitor none \\
    -qmp tcp:127.0.0.1:4444,server=on,wait=off -device virtio-vga
Loopback QMP availability still depends on host policy. Never attach host disks.
''')
for name in names:
    option='-version' if name in ['xorriso','unsquashfs'] else '--version'
    check=subprocess.run([str(root/'wrappers'/name),option],capture_output=True,text=True)
    (root/(name+'-version.txt')).write_text(check.stdout+check.stderr)
    version_text=check.stdout+check.stderr
    print(name+' version exit='+str(check.returncode)+' '+version_text[:300],flush=True)
    expected_unsquashfs_version_exit=(name=='unsquashfs' and check.returncode==1 and 'unsquashfs version' in version_text.lower())
    if check.returncode and not expected_unsquashfs_version_exit:
        raise RuntimeError(name+' bundled startup failed')
digest=[]
for path in sorted(root.rglob('*')):
    if path.is_file():
        digest.append(hashlib.sha256(path.read_bytes()).hexdigest()+'  '+str(path.relative_to(root)))
(root/'SHA256SUMS').write_text('\n'.join(digest)+'\n')
print('Bundled and checked '+', '.join(names)+' in '+str(root))
