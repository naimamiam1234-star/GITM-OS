"""Capture actual local Qt widgets, with no scan fixtures or vehicle traffic.
Run: QT_QPA_PLATFORM=offscreen python3 ui-work/visual-validation/render.py
"""
import os,sys,json,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('GITM_STATE','/tmp/gitm-stability-visual/state')
for path in (ROOT/'runtime',ROOT/'source/GearDiag-Raw-Build/app',ROOT/'ui-work/diag-integration'):
 sys.path.insert(0,str(path))
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
import native,professional_ui,business_workspace

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--output',default='/tmp/gitm-stability-visual');args=parser.parse_args()
 out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
 app=QApplication.instance() or QApplication([]);window=native.Window();professional_ui.install(window);shell=window.professional_shell
 # English layout creates directly comparable captures; labels remain actual translations.
 shell.lang.setCurrentIndex(2)
 manifest={'capture':'actual local Window widget rasterization','acquisition':'none; no synthetic results','screenshots':[]}
 for theme in ('light','dark'):
  for font in (16,20):
   shell.theme=theme;shell.font=font;shell.apply_theme()
   for width,height in ((1280,800),(1000,650)):
    window.resize(width,height);window.show()
    pages=[('home',shell.home),('diagnostics',window.diagnosis_page),('live',lambda:(window.diagnosis_page(),window.diagnostic_workspace.tabs.setCurrentIndex(2))),('sourceaudit',window.sources_page),('customers',lambda:business_workspace.customers(window)),('invoices',lambda:business_workspace.invoices(window))]
    for name,show in pages:
     show()
     if name=='diagnostics':window.diagnostic_workspace.tabs.setCurrentIndex(0)
     for _ in range(3):app.processEvents();QTest.qWait(30)
     filename=f'{theme}-font{font}-{width}x{height}-{name}.png';pixmap=window.grab()
     if not pixmap.save(str(out/filename)):raise RuntimeError(f'Could not write {filename}')
     geometry={}
     if name=='live':
      for key,widget in [('live_table',window.diagnostic_workspace.live_table),('graph',window.diagnostic_workspace.graph),('connection',window.diagnostic_workspace.connection)]:
       point=widget.mapTo(window,widget.rect().topLeft());geometry[key]=[point.x(),point.y(),widget.width(),widget.height()]
     manifest['screenshots'].append({'geometry':geometry,'file':filename,'page':name,'theme':theme,'font_px':font,'requested_size':[width,height],'actual_size':[pixmap.width(),pixmap.height()]})
     (out/'manifest.json').write_text(json.dumps(manifest,indent=2))
 window.close();app.processEvents()
 print(json.dumps({'captures':len(manifest['screenshots']),'output':str(out)}))
if __name__=='__main__':main()
