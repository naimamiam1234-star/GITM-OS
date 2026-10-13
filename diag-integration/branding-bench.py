"""Actual installed identity, resource library and video-decoder evidence."""
import os,sys,json,time,hashlib
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer,QUrl
from PySide6.QtMultimedia import QMediaPlayer,QVideoSink
import branding,resource_library,native
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True);app=QApplication([])
rows=resource_library.catalog();local=[r for r in rows if r['present']];proof={'local_resources':len(local),'sdk_archives':sum(r.get('category')=='SDK source archive' and r['present'] for r in rows),'obdb_archives':sum(r.get('category')=='OBDb reference' and r['present'] for r in rows),'wallpapers':len(branding.wallpaper_choices()),'videos':{}}
if proof['sdk_archives']!=12 or proof['obdb_archives']!=885 or proof['wallpapers']!=18:raise RuntimeError('Installed resource counts mismatch')
w=native.Window();w.resize(1280,800);w.show();shell=w.professional_shell
for mode in ('light','dark'):
 shell.set_theme(mode);shell.home();app.processEvents();w.grab().save(str(out/('autodiag-home-'+mode+'.png')))
 resource_library.show(w);app.processEvents();w.grab().save(str(out/('resource-library-'+mode+'.png')))
w.close()
# Decoding real clips is separate from actual boot frame evidence.
for mode in ('dark','light'):
 player=QMediaPlayer();sink=QVideoSink();player.setVideoSink(sink);count=[0];hashes=set()
 def frame(f):
  if f.isValid():
   im=f.toImage()
   if not im.isNull():
    count[0]+=1
    if count[0] in (1,25,50):
     p=out/(mode+'-video-'+str(count[0])+'.png');im.save(str(p));hashes.add(hashlib.sha256(p.read_bytes()).hexdigest())
 sink.videoFrameChanged.connect(frame);player.setSource(QUrl.fromLocalFile(str(branding.session_clip(mode))));player.play();end=time.monotonic()+4
 while time.monotonic()<end:app.processEvents();time.sleep(.01)
 player.stop();proof['videos'][mode]={'decoded_frames':count[0],'distinct_frames':len(hashes)}
 if count[0]<25 or len(hashes)<2:raise RuntimeError('Installed video decode failed')
(out/'proof.json').write_text(json.dumps(proof,indent=2));print('PASS: installed identity, resource and decoder evidence')
