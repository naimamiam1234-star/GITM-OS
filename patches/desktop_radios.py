"""Asynchronous, measured desktop connectivity. No synthetic online states."""
import os, shutil, re
from pathlib import Path
from PySide6.QtCore import QObject, QProcess, QTimer, Signal
from PySide6.QtWidgets import QLabel,QPushButton,QLineEdit,QListWidget,QListWidgetItem,QHBoxLayout

def fields(line):
 result=[];current='';escaped=False
 for char in line:
  if escaped:current+=char;escaped=False
  elif char=='\\':escaped=True
  elif char==':':result.append(current);current=''
  else:current+=char
 result.append(current)
 return result

def classify_wifi(out,ok,enabled):
 if not ok:return 'تعذر قراءة الخدمة',{'kind':'error','signal':0}
 rows=[fields(x) for x in out.splitlines()]
 hardware=[x for x in rows if len(x)>=3 and x[0]=='wifi']
 connected=[x for x in hardware if x[1]=='connected']
 if connected:return connected[0][2],{'kind':'connected','signal':0}
 if not hardware:return 'غير متوفر',{'kind':'missing','signal':0}
 return ('مفعّل · غير متصل',{'kind':'on','signal':0}) if enabled else ('متوقف',{'kind':'off','signal':0})

def battery_info(root=Path('/sys/class/power_supply')):
 for p in sorted(root.glob('*')):
  try:
   if (p/'type').read_text().strip()!='Battery':continue
   if (p/'present').exists() and (p/'present').read_text().strip()=='0':continue
   value=max(0,min(100,int((p/'capacity').read_text())))
   status=(p/'status').read_text().strip()
   return {'present':True,'percent':value,'charging':status=='Charging','text':f'{value}% · '+{'Charging':'يشحن','Discharging':'على البطارية','Full':'مكتملة'}.get(status,status)}
  except (OSError,ValueError):continue
 return {'present':False,'percent':0,'charging':False,'text':'لا توجد بطارية'}

def battery(root=Path('/sys/class/power_supply')):
 return battery_info(root)['text']

def state_icon(name,state):
 from PySide6.QtGui import QPixmap,QPainter,QPen,QColor,QIcon
 from PySide6.QtCore import Qt,QRectF
 pix=QPixmap(44,44);pix.fill(Qt.transparent);p=QPainter(pix);p.setRenderHint(QPainter.Antialiasing)
 kind=state.get('kind','unknown');active=kind in ('connected','on')
 light=state.get('light',False)
 color=QColor(('#0767af' if light else '#42b7ff') if active else ('#455c79' if light else '#8998ad'));p.setPen(QPen(color,2.5,Qt.SolidLine,Qt.RoundCap))
 if name=='wifi':
  strength=state.get('signal',0)
  for i,(threshold,rect) in enumerate([(0,QRectF(15,22,14,10)),(35,QRectF(9,14,26,20)),(70,QRectF(3,6,38,30))]):
   p.setPen(QPen(QColor(('#0767af' if light else '#42b7ff') if kind=='connected' and strength>=threshold else '#65778e'),2.5,Qt.SolidLine,Qt.RoundCap));p.drawArc(rect,35*16,110*16)
  p.setBrush(color);p.drawEllipse(20,33,4,4)
 elif name=='bluetooth':
  p.drawLine(21,5,21,38);p.drawLine(21,5,32,16);p.drawLine(32,16,10,31);p.drawLine(10,12,32,27);p.drawLine(32,27,21,38)
  if kind=='connected':
   p.setBrush(QColor('#55e5b0'));p.setPen(Qt.NoPen);p.drawEllipse(33,17,7,7)
 elif name=='volume':
  p.drawLine(5,17,12,17);p.drawLine(12,17,23,8);p.drawLine(23,8,23,36);p.drawLine(23,36,12,27);p.drawLine(12,27,5,27);p.drawLine(5,27,5,17)
  if state.get('mute'):
   p.drawLine(29,17,38,27);p.drawLine(38,17,29,27)
  elif kind=='on':
   if state.get('percent',0)>0:p.drawArc(QRectF(18,12,17,20),-65*16,130*16)
   if state.get('percent',0)>50:p.drawArc(QRectF(16,6,26,32),-65*16,130*16)
 elif name=='battery':
  present=state.get('present',False);level=state.get('percent',0)
  color=QColor('#ff5a66' if level<=15 and present else '#087d57' if light and state.get('charging') else '#4fe0a5' if state.get('charging') else '#405978' if light else '#b8d8f9');p.setPen(QPen(color,2.5));p.setBrush(Qt.NoBrush)
  p.drawRoundedRect(QRectF(4,13,32,18),3,3);p.drawLine(39,19,39,25)
  if present:
   p.fillRect(QRectF(7,16,26*level/100,12),color)
   if state.get('charging'):
    p.setPen(QPen(QColor('#fff'),2));p.drawLine(23,10,16,22);p.drawLine(16,22,25,22);p.drawLine(25,22,19,35)
  else:kind='missing'
 elif name=='sync':
  p.setPen(QPen(QColor(('#0767af' if light else '#42b7ff') if state.get('busy') else '#405978' if light else '#b8d8f9'),2.5))
  if state.get('busy'):p.translate(22,22);p.rotate(state.get('phase',0)*30);p.translate(-22,-22)
  p.drawArc(QRectF(8,8,28,28),25*16,135*16);p.drawArc(QRectF(8,8,28,28),205*16,135*16)
  p.drawLine(8,8,8,18);p.drawLine(8,18,18,18);p.drawLine(36,36,36,26);p.drawLine(36,26,26,26)
 if kind=='missing':
  p.setPen(QPen(QColor('#ff4355' if name=='battery' else '#455c79' if light else '#8998ad'),3.5,Qt.SolidLine,Qt.RoundCap));p.drawLine(14,12,30,30);p.drawLine(30,12,14,30)
 elif kind=='off':
  p.setPen(QPen(QColor('#c0c8d4'),2.5));p.drawLine(7,37,36,7)
 p.end();return QIcon(pix)

class Radios(QObject):
 changed=Signal()
 def __init__(self,desktop):
  super().__init__(desktop);self.desktop=desktop;self.pending=[];self.busy=False
  self.audio_state={'kind':'unknown'};self.wifi='غير معروف';self.bluetooth='غير معروف';self.networks=[];self.devices=[];self.wifi_state={'kind':'unknown','signal':0};self.bluetooth_state={'kind':'unknown'}
  self.timer=QTimer(self);self.timer.timeout.connect(self.refresh);self.timer.start(15000)
  self.refresh()
 def run(self,args,done):
  self.pending.append((args,done));self.next()
 def next(self):
  if self.busy or not self.pending:return
  args,done=self.pending.pop(0)
  if not shutil.which(args[0]):done(False,'الأداة غير متوفرة');self.next();return
  self.busy=True;self.changed.emit();p=QProcess(self);self.process=p
  env=p.processEnvironment();env=__import__('PySide6.QtCore',fromlist=['QProcessEnvironment']).QProcessEnvironment.systemEnvironment();env.insert('LC_ALL','C');p.setProcessEnvironment(env)
  timeout=QTimer(p);timeout.setSingleShot(True);timeout.timeout.connect(p.kill)
  completed=False
  def finish(code,status):
   nonlocal completed
   if completed:return
   completed=True
   timeout.stop();out=bytes(p.readAllStandardOutput()).decode(errors='replace');err=bytes(p.readAllStandardError()).decode(errors='replace')
   self.busy=False;self.changed.emit()
   try:done(code==0,out if code==0 else err or 'تعذر تنفيذ العملية')
   finally:p.deleteLater();self.next()
  p.finished.connect(finish)
  p.errorOccurred.connect(lambda error:finish(-1,None) if error==QProcess.FailedToStart else None)
  timeout.start(12000);p.start(args[0],args[1:])
 def refresh(self):
  if self.busy or self.pending:return
  def wifi(ok,out):
   self.wifi,self.wifi_state=classify_wifi(out,ok,getattr(self,'wifi_enabled',True));self.changed.emit()
   connected=self.wifi_state['kind']=='connected'
   if connected:
    def signal(ok2,out2):
     signals=[fields(x) for x in out2.splitlines()] if ok2 else []
     values=[int(x[1]) for x in signals if len(x)>=2 and x[0]=='*' and x[1].isdigit()]
     self.wifi_state['signal']=values[0] if values else 0;self.changed.emit()
    self.run(['nmcli','-t','-f','IN-USE,SIGNAL','device','wifi','list','--rescan','no'],signal)
  def bluetooth(ok,out):
   on=ok and 'Powered: yes' in out
   self.bluetooth='مفعّل' if on else 'متوقف' if ok and 'Controller ' in out else 'غير متوفر' if ok else 'تعذر قراءة الخدمة'
   self.bluetooth_state={'kind':'on' if on else 'off' if ok and 'Controller ' in out else 'missing' if ok else 'error'};self.changed.emit()
   if on:
    def connections(ok2,out2):
     if ok2 and any(x.startswith('Device ') for x in out2.splitlines()):self.bluetooth_state={'kind':'connected'};self.bluetooth='متصل'
     self.changed.emit()
    self.run(['bluetoothctl','devices','Connected'],connections)
  def volume(ok,out):
   values=re.findall(r'(\d+)%',out) if ok else []
   self.audio_state={'kind':'on' if values else 'missing','percent':int(values[0]) if values else 0,'mute':self.audio_state.get('mute',False)}
   self.changed.emit()
   if values:
    def mute(ok2,out2):
     if ok2:self.audio_state['mute']='yes' in out2
     self.changed.emit()
    self.run(['pactl','get-sink-mute','@DEFAULT_SINK@'],mute)
  self.run(['pactl','get-sink-volume','@DEFAULT_SINK@'],volume)
  def radio(ok,out):
   self.wifi_enabled=out.strip()=='enabled' if ok else True
   self.run(['nmcli','-t','-f','TYPE,STATE,CONNECTION','device'],wifi)
  self.run(['nmcli','radio','wifi'],radio)
  self.run(['bluetoothctl','show'],bluetooth)
 def show(self,kind):
  title='شبكات Wi-Fi' if kind=='wifi' else 'أجهزة Bluetooth'
  for existing in self.desktop.dialogs:
   if existing.windowTitle()==title:existing.showNormal();existing.raise_();existing.activateWindow();return
  self.desktop.control.hide();self.desktop.status_buttons['chevron'].setChecked(False)
  d,v=self.desktop.panel('شبكات Wi-Fi' if kind=='wifi' else 'أجهزة Bluetooth')
  search=QLineEdit();search.setPlaceholderText('بحث في النتائج…');v.addWidget(search)
  status=QLabel('');status.setWordWrap(True);v.addWidget(status)
  listing=QListWidget();listing.setMinimumHeight(250);v.addWidget(listing)
  row=QHBoxLayout();v.addLayout(row)
  refresh=QPushButton('⟳ بحث / تحديث');row.addWidget(refresh)
  manage=QPushButton('إدارة الاتصال');row.addWidget(manage)
  manage.clicked.connect(lambda:self.desktop.launch(kind,['nm-connection-editor'] if kind=='wifi' else ['blueman-manager']))
  def filter_rows(text):
   for i in range(listing.count()):listing.item(i).setHidden(text.casefold() not in listing.item(i).text().casefold())
  search.textChanged.connect(filter_rows)
  def result(ok,out):
   if not d.isVisible():return
   refresh.setEnabled(True);listing.clear()
   if not ok:status.setText('تعذر قراءة الحالة: '+out);listing.addItem('تحقق من خدمة الاتصال أو افتح إدارة الاتصال.');return
   if kind=='wifi':
    rows=[fields(x) for x in out.splitlines()]
    for x in rows:
     if len(x)<4:continue
     active,ssid,signal,security=x[:4]
     label=('● متصل · ' if active=='*' else '')+(ssid or 'شبكة مخفية')+f' · {signal}% · '+security
     listing.addItem(label)
    status.setText('الشبكة الحالية: '+self.wifi+' · افتح إدارة الاتصال للاتصال أو إدخال كلمة المرور.')
   else:
    connected=out.split('\n---connected---\n')
    known=connected[0].splitlines();active=set()
    if len(connected)>1:active={x.split()[1] for x in connected[1].splitlines() if x.startswith('Device ') and len(x.split())>=2}
    for x in known:
     parts=x.split(' ',2)
     if len(parts)==3 and parts[0]=='Device':listing.addItem(('● متصل · ' if parts[1] in active else '')+parts[2]+' · '+parts[1])
    status.setText('Bluetooth: '+self.bluetooth+' · البحث والاقتران عبر مدير Bluetooth.')
   if listing.count()==0:listing.addItem('لا توجد نتائج متاحة')
   filter_rows(search.text())
  def scan():
   refresh.setEnabled(False);status.setText('جارٍ قراءة الحالة الفعلية…')
   state=self.wifi_state if kind=='wifi' else self.bluetooth_state
   if state['kind']=='missing':
    refresh.setEnabled(True);listing.clear();status.setText('لا يوجد محول Wi-Fi متاح.' if kind=='wifi' else 'لا يوجد محول Bluetooth متاح.');return
   if kind=='wifi':
    self.run(['nmcli','--wait','8','-t','-f','IN-USE,SSID,SIGNAL,SECURITY','device','wifi','list','--rescan','yes'],result)
   else:
    def known(ok,out):
     if not ok:result(False,out);return
     self.run(['bluetoothctl','devices','Connected'],lambda ok2,out2:result(True,out+'\n---connected---\n'+(out2 if ok2 else '')))
    self.run(['bluetoothctl','devices'],known)
  refresh.clicked.connect(scan);d.show();scan()


