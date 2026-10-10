"""Opt-in gallery of actual desktop actions inside a disposable boot-test guest."""
import json,subprocess,sys
from pathlib import Path
from PySide6.QtCore import QObject,QTimer,QProcess
from PySide6.QtWidgets import QApplication,QMessageBox
def emit(value):
 subprocess.run(['logger','-t','gitm-gallery',value],check=False)
def windows():
 result=subprocess.run(['wmctrl','-lp'],capture_output=True,text=True,timeout=4)
 return [x for x in result.stdout.splitlines() if 'GITM OS' not in x]
class Gallery(QObject):
 def __init__(self,w):
  super().__init__(w);self.w=w;self.index=0;self.records=[];self.native=None
  self.steps=[
   ('desktop',lambda:None),
   ('control-center',w.toggle_control),
   ('wifi',lambda:w.status_buttons['wifi'].click()),
   ('bluetooth',lambda:w.status_buttons['bluetooth'].click()),
   ('battery-power',lambda:w.status_buttons['battery'].click()),
   ('search',lambda:w.search.setFocus()),
   ('sync',lambda:w.status_buttons['sync'].click()),
   ('settings',w.settings),('updates',w.updates),('appearance',w.choose_appearance),
   ('airplane-confirm',w.toggle_airplane),
   ('suspend-confirm',lambda:w.confirm_power('suspend')),
   ('reboot-confirm',lambda:w.confirm_power('reboot')),
   ('shutdown-confirm',lambda:w.confirm_power('poweroff')),
  ]
  for key in ['files','browser','photos','media','calculator','install','documents']:
   self.steps.append(('app-'+key,lambda k=key:w.app_buttons[k].click()))
  for key,cmd in [('network',['nm-connection-editor']),('bluetooth-manager',['blueman-manager']),('audio',['pavucontrol']),('screen-power',['systemsettings5']),('keyboard',['onboard']),('processes',['plasma-systemmonitor']),('accounts',['systemsettings5','kcm_users']),('system-updates',['plasma-discover'])]:
   self.steps.append((key,lambda k=key,c=cmd:w.launch(k,c)))
 def cleanup(self):
  for dialog in list(self.w.dialogs):dialog.reject()
  for dialog in QApplication.topLevelWidgets():
   if isinstance(dialog,QMessageBox):dialog.done(QMessageBox.Cancel)
  self.w.control.hide();self.w.status_buttons['chevron'].setChecked(False);self.w.search.clear()
  for line in windows():
   subprocess.run(['wmctrl','-ic',line.split()[0]],check=False)
  for process in self.w.processes.values():
   if process.state()!=QProcess.NotRunning:
    process.blockSignals(True);process.terminate()
 def next(self):
  self.cleanup()
  if self.index==len(self.steps):
   self.native=QProcess(self);self.native.setProgram(sys.executable);self.native.setArguments([str(Path(__file__).with_name('gallery_native.py'))])
   self.native.finished.connect(self.done);self.native.start();return
  name,fn=self.steps[self.index];self.index+=1
  QTimer.singleShot(8000,lambda:self.capture(name))
  try:fn()
  except Exception as e:emit('GITM_GALLERY_ERROR|'+name+'|'+str(e))
 def capture(self,name):
  self.records.append({'name':name,'windows':windows()})
  emit('GITM_GALLERY_FRAME|'+name)
  QTimer.singleShot(5000,self.next)
 def done(self,*args):
  emit('GITM_GALLERY_REPORT|'+json.dumps(self.records,ensure_ascii=True))
  emit('GITM_GALLERY_DONE')
def start(w):
 w.gallery=Gallery(w);w.gallery.next()
