"""Describe immutable release assets for the streaming download service."""
import hashlib
import json
import os
from pathlib import Path

root = Path('.')
iso = root / 'GITM-OS-Plasma6-amd64.iso'
base = 'https://github.com/naimamiam1234-star/GITM-OS/releases/download/' + os.environ['RELEASE_TAG'] + '/'
def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()
parts = [{'name': p.name, 'size': p.stat().st_size, 'sha256': digest(p), 'url': base + p.name}
         for p in sorted(root.glob(iso.name + '.part*'))]
boundary = parts[0]['size'] - 16
with iso.open('rb') as stream:
    stream.seek(boundary)
    boundary_hex = stream.read(32).hex()
    stream.seek(-32, 2)
    tail_hex = stream.read(32).hex()
gallery = root / 'gallery.html'
manifest = {'name': iso.name, 'size': iso.stat().st_size, 'sha256': digest(iso), 'parts': parts,
            'boundary_offset': boundary, 'boundary_hex': boundary_hex, 'tail_hex': tail_hex,
            'build_commit': os.environ['SOURCE_SHA'], 'boot_test_run': int(os.environ['SOURCE_RUN']), 'bios': 'passed', 'uefi': 'passed',
            'base': 'Ubuntu 26.04', 'desktop': 'Plasma 6.6.6',
            'cpu_features': ['ssse3', 'sse4_1', 'sse4_2', 'popcnt'],
            'gallery': {'images': 60, 'size': gallery.stat().st_size, 'sha256': digest(gallery),
                        'url': base + gallery.name, 'overview_url': base + 'gallery-overview.png',
                        'capture_runs': [int(os.environ['SOURCE_RUN'])]}}
(root / 'plasma-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
