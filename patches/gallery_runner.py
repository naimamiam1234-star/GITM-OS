"""Opt-in gallery of actual desktop actions inside a disposable boot-test guest."""
import json,subprocess,sys
from pathlib import Path
from PySide6.QtCore import QObject,QTimer,QProcess,Qt
from PySide6.QtWidgets import QApplication,QMessageBox
def emit(value):
 subprocess.run(['logger','-t','gitm-gallery',value],check=False)
def windows():
 result=subprocess.run(['wmctrl','-lp'],capture_output=True,text=True,timeout=4)
 return [x for x in result.stdout.splitlines() if 'GITM OS' not in x]
class Gallery(QObject):
 def __init__(self,w):
  super().__init__(w);self.w=w;self.index=0;self.records=[];self.native=None;self.focused='gitm.gallery.browser=1' in Path('/proc/cmdline').read_text()
  self.steps=[
   ('desktop',lambda:None),
   ('control-center',w.toggle_control),
   ('wifi',lambda:w.status_buttons['wifi'].click()),
   ('bluetooth',lambda:w.status_buttons['bluetooth'].click()),
   ('volume-popup',w.audio),
   ('battery-power',lambda:w.status_buttons['battery'].click()),
   ('search',lambda:w.search.setFocus()),
   ('sync',lambda:w.status_buttons['sync'].click()),
   ('settings',w.settings),('updates',w.updates),('appearance',w.choose_appearance),
   ('appearance-light',self.light_appearance),('desktop-light',lambda:None),
   ('control-center-light',self.light_control),
   ('suspend-confirm',lambda:w.confirm_power('suspend')),
   ('reboot-confirm',lambda:w.confirm_power('reboot')),
   ('shutdown-confirm',lambda:w.confirm_power('poweroff')),
  ]
  for key in ['files','browser','photos','media','calculator','install','documents']:
   self.steps.append(('app-'+key,lambda k=key:w.app_buttons[k].click()))
  for key,cmd in [('network',['nm-connection-editor']),('bluetooth-manager',['blueman-manager']),('audio',['pavucontrol']),('screen-power',['systemsettings5']),('keyboard',['onboard']),('processes',['plasma-systemmonitor']),('accounts',['systemsettings5','kcm_users']),('system-updates',['plasma-discover'])]:
   self.steps.append((key,lambda k=key,c=cmd:w.launch(k,c)))
  if self.focused:self.steps=[step for step in self.steps if step[0] in {'desktop','app-browser','keyboard','system-updates'}]
 def cleanup(self):
  self.w.popups.close()
  for dialog in list(self.w.dialogs):dialog.reject()
  for dialog in QApplication.topLevelWidgets():
   if isinstance(dialog,QMessageBox):
    button=dialog.button(QMessageBox.Cancel) or dialog.button(QMessageBox.No) or dialog.button(QMessageBox.Ok)
    if button:button.click()
    else:dialog.reject()
  self.w.control.hide();self.w.status_buttons['chevron'].setChecked(False);self.w.search.clear()
  for line in windows():
   subprocess.run(['wmctrl','-ic',line.split()[0]],check=False)
  for process in self.w.processes.values():
   if process.state()!=QProcess.NotRunning:
    process.blockSignals(True);process.terminate()
 def next(self):
  self.cleanup()
  if self.index==len(self.steps):
   if self.focused:self.done();return
   self.native=QProcess(self);self.native.setProgram(sys.executable);self.native.setArguments([str(Path(__file__).with_name('gallery_native.py'))])
   self.native.finished.connect(self.done);self.native.start();return
  name,fn=self.steps[self.index];self.index+=1
  if name not in {'appearance-light','desktop-light','control-center-light'} and self.w.appearance['mode']!='dark':
   self.w.appearance['mode']='dark';self.w.apply_appearance()
  QTimer.singleShot(10000 if name.startswith('app-') or name in {'screen-power','processes','accounts','system-updates'} else 4000,lambda:self.capture(name))
  try:fn()
  except Exception as e:emit('GITM_GALLERY_ERROR|'+name+'|'+str(e))
 def light_appearance(self):
  self.w.appearance['mode']='light';self.w.apply_appearance();self.w.choose_appearance()
 def light_control(self):
  self.w.appearance['mode']='light';self.w.apply_appearance();self.w.toggle_control()
 def capture(self,name):
  popup_keys={'control-center':'control','control-center-light':'control','wifi':'wifi','bluetooth':'bluetooth','volume-popup':'volume','battery-power':'power','suspend-confirm':'power','reboot-confirm':'power','shutdown-confirm':'power'}
  if name in popup_keys:
   p=QApplication.activePopupWidget()
   valid=p is not None and p.isVisible() and p.key==popup_keys[name] and bool(p.windowFlags() & Qt.FramelessWindowHint)
   emit('GITM_POPUP|'+name+'|'+('PASS' if valid else 'FAIL'))
   if not valid:emit('GITM_GALLERY_ERROR|'+name+'|Expected one frameless status popup')
  if name=='app-browser' and not any('Falkon' in line for line in windows()):
   emit('GITM_GALLERY_ERROR|app-browser|No actual Falkon window');self.done();return
  if name=='app-browser':
   process=self.w.processes.get('browser')
   if process and process.processId():
    try:emit('GITM_BROWSER_POLICY|'+Path('/proc/'+str(process.processId())+'/attr/current').read_text().strip())
    except OSError as error:emit('GITM_BROWSER_POLICY_ERROR|'+str(error))
  if name=='keyboard':subprocess.run(['dbus-send','--session','--type=method_call','--dest=org.onboard.Onboard','/org/onboard/Onboard/Keyboard','org.onboard.Onboard.Keyboard.Show'],check=False)
  if name in {'app-browser','keyboard','system-updates'}:
   items=windows()
   if items:subprocess.run(['wmctrl','-ia',items[-1].split()[0]],check=False)
  for cmd in [['xset','s','off'],['xset','-dpms'],['xset','s','reset']]:subprocess.run(cmd,check=False)
  for line in windows():emit('GITM_GALLERY_WINDOW|'+name+'|'+line)
  for file in (Path.home()/'.local/share/gitm').glob('*.log'):
   for line in file.read_text(errors='replace').splitlines()[-4:]:emit('GITM_GALLERY_APPLOG|'+name+'|'+file.name+'|'+line[:500])
  self.records.append({'name':name,'windows':windows()})
  emit('GITM_GALLERY_FRAME|'+name)
  QTimer.singleShot(2000,self.next)
 def done(self,*args):
  emit('GITM_GALLERY_REPORT|'+json.dumps(self.records,ensure_ascii=True))
  emit('GITM_GALLERY_DONE')
def start(w):
 w.gallery=Gallery(w);w.gallery.next()


