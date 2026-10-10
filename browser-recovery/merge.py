from pathlib import Path
import json
from PIL import Image,ImageStat
root=Path('dist');report=(root/'gallery/guest-report.txt').read_text()
lines=[line for line in report.splitlines() if 'GITM_GALLERY_WINDOW|app-browser|' in line]
if not any('Falkon' in line for line in lines):raise RuntimeError('Falkon did not open: '+str(lines))
if 'FATAL:credentials' in report or 'GITM_GALLERY_ERROR|' in report:raise RuntimeError('Focused application test failed')
for name in ['desktop','app-browser','keyboard','system-updates']:
 image=root/'gallery'/(name+'.png')
 if sum(ImageStat.Stat(Image.open(image).convert('RGB')).stddev)/3<8:raise RuntimeError('Inactive capture '+name)
old=(Path('previous/gallery/guest-report.txt')).read_text()
(root/'gallery/guest-report.txt').write_text(old+'\nFOCUSED_RECAPTURE_AFTER_BROWSER_FIX\n'+report)
(root/'gallery/capture-provenance.json').write_text(json.dumps({'unchanged_views_run':38011421948,'recaptured_views':['desktop','app-browser','keyboard','system-updates'],'note':'Same desktop design; browser AppArmor correction added in the current ISO.'},indent=2))
print('BROWSER_WINDOW_AND_FOCUSED_CAPTURES_VERIFIED')
