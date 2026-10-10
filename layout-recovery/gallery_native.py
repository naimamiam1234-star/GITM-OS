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
def emit(s):subprocess.run(['logger','-t','gitm-gallery',s],check=False)
def next():
 global index
 if index==len(steps):
  emit('GITM_GALLERY_NATIVE_DONE');app.quit();return
 name,fn=steps[index];index+=1
 try:w.go_home();fn()
 except Exception as e:emit('GITM_GALLERY_ERROR|'+name+'|'+str(e))
 QTimer.singleShot(4000,lambda:capture(name))
def capture(name):
 for cmd in [['xset','s','off'],['xset','-dpms'],['xset','s','reset']]:subprocess.run(cmd,check=False)
 emit('GITM_GALLERY_FRAME|'+name);QTimer.singleShot(5000,next)
QTimer.singleShot(4000,next);sys.exit(app.exec())
