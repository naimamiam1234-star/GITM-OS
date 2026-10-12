from pathlib import Path
import json,re,os
from PIL import Image,ImageStat
root=Path('dist');report=(root/'gallery/guest-report.txt').read_text()
lines=[line for line in report.splitlines() if 'GITM_GALLERY_WINDOW|app-browser|' in line]
if not any('Falkon' in line for line in lines):raise RuntimeError('Falkon did not open: '+str(lines))
if 'FATAL:credentials' in report or 'GITM_GALLERY_ERROR|' in report:raise RuntimeError('Application test failed')
if 'GITM_BROWSER_POLICY|gitm-falkon' not in report:raise RuntimeError('Browser-specific policy was not active')
frames=set(re.findall(r'GITM_GALLERY_FRAME\|([a-z0-9-]+)',report))
if len(frames)!=60:raise RuntimeError(f'Expected 60 fresh captures, found {len(frames)}')
for name in frames:
 image=root/'gallery'/(name+'.png')
 if sum(ImageStat.Stat(Image.open(image).convert('RGB')).stddev)/3<8:raise RuntimeError('Inactive capture '+name)
(root/'gallery/capture-provenance.json').write_text(json.dumps({'capture_run':os.environ.get('GITHUB_RUN_ID'),'views':sorted(frames),'note':'All screenshots recaptured from the current ISO; no inherited gallery.'},indent=2))
print('BROWSER_POLICY_AND_60_ACTUAL_CAPTURES_VERIFIED')
