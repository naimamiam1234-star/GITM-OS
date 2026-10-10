"""Reject a Plasma preview unless its source run and guest evidence are complete."""
import hashlib
from pathlib import Path
from PIL import Image, ImageStat

root = Path('download/iso')
iso = next(root.glob('*.iso'))
expected = next(root.glob('*.iso.sha256')).read_text().split()[0]
with iso.open('rb') as stream:
    actual = hashlib.file_digest(stream, 'sha256').hexdigest()
assert actual == expected, 'ISO checksum mismatch'
for mode in ('bios', 'uefi'):
    log = (root / (mode + '-serial.log')).read_text(errors='replace')
    assert 'GITM_DESKTOP_VISIBLE' in log, mode + ': no visible desktop'
    assert 'GITM_PLASMA_SESSION|plasmashell 6.' in log, mode + ': no Plasma/KWin evidence'
gallery = Path('download/gallery')
report = (gallery / 'guest-report.txt').read_text()
assert 'GITM_NETWORK_RELEASE_OK|resolute' in report, 'No verified Ubuntu repository connection'
assert 'GITM_CATALOG_OK' in report, 'No populated Ubuntu application catalogue'
assert 'GITM_GALLERY_DONE' in report
assert 'GITM_GALLERY_ERROR|' not in report
for name in ('desktop', 'app-files', 'app-browser', 'screen-power', 'accounts', 'system-updates'):
    assert (gallery / (name + '.png')).is_file(), 'Missing screenshot: ' + name
    with Image.open(gallery / (name + '.png')) as image:
        width, height = image.size
        content = image.crop((width // 4, height // 4, 3 * width // 4, 3 * height // 4)).convert('RGB')
        assert max(ImageStat.Stat(content).stddev) > 6, 'Empty central screenshot: ' + name
assert any('GITM_GALLERY_WINDOW|screen-power|' in line and 'system settings' in line.lower() for line in report.splitlines()), 'No actual settings window recorded'
assert len(list(gallery.glob('*.png'))) >= 60, 'Incomplete application gallery'
packages = (root / 'packages.txt').read_text()
assert any(line.startswith('plasma-workspace 4:6.') for line in packages.splitlines())
print('ISO checksum, BIOS/UEFI Plasma 6 session, and full guest gallery verified.')
