"""Open every AutoDiag home tile and workshop page; never run vehicle writes."""
import sys,subprocess,json
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication,QLabel
from native import Window
import workshop_tools
app=QApplication(sys.argv);w=Window();w.showMaximized()
steps=[('autodiag-home',lambda:w.go_home())]
for i,card in enumerate(w.home_cards):
 labels=[x.text() for x in card.findChildren(QLabel) if x.objectName()=='cardlabel']
 steps.append(('autodiag-'+str(i+1).zfill(2),lambda c=card:c.click()))
for name in ['customers','invoices','invoice_history','camera','pdf','media','calculator']:
 steps.append(('workshop-'+name.replace('_','-'),lambda n=name:getattr(workshop_tools,n)(w)))
if hasattr(w,'split_page'):steps.append(('split-screen',w.split_page))
index=0
service_process=None
def os_service(kind):
 global service_process
 from pathlib import Path
 service_process=subprocess.Popen([sys.executable,str(Path(__file__).parent/'system_services.py'),kind])
steps.extend([('os-camera',lambda:os_service('camera')),('os-update-center',lambda:os_service('updates'))])
def emit(s):subprocess.run(['logger','-t','gitm-gallery',s],check=False)
import gallery_bench
gallery_bench.setup(w,steps,emit)
def next():
 global index,service_process
 if service_process is not None:
  if service_process.poll() is not None and service_process.returncode!=0:emit('GITM_GALLERY_ERROR|os-service|Service startup failed')
  elif service_process.poll() is None:service_process.terminate();service_process.wait(timeout=5)
  service_process=None
 if index==len(steps):
  emit('GITM_GALLERY_NATIVE_DONE');app.quit();return
 name,fn=steps[index];index+=1
 try:w.go_home();fn()
 except Exception as e:emit('GITM_GALLERY_ERROR|'+name+'|'+str(e))
 QTimer.singleShot(10000 if name=='diag-bench-summary' else 6000 if name=='diag-bench-live' else 4000,lambda:capture(name))
def capture(name):
 subprocess.run(['xdotool','mousemove','640','80'],check=False)
 for cmd in [['xset','s','off'],['xset','-dpms'],['xset','s','reset']]:subprocess.run(cmd,check=False)
 emit('GITM_GALLERY_FRAME|'+name);QTimer.singleShot(2000,next)
QTimer.singleShot(4000,next);sys.exit(app.exec())

