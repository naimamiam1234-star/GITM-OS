"""Asynchronous, measured desktop connectivity. No synthetic online states."""
import os, shutil
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

def battery(root=Path('/sys/class/power_supply')):
 for p in sorted(root.glob('*')):
  try:
   if (p/'type').read_text().strip()!='Battery':continue
   if (p/'present').exists() and (p/'present').read_text().strip()=='0':continue
   value=max(0,min(100,int((p/'capacity').read_text())))
   status=(p/'status').read_text().strip()
   return f'{value}% · '+{'Charging':'يشحن','Discharging':'على البطارية','Full':'مكتملة'}.get(status,status)
  except (OSError,ValueError):continue
 return 'لا توجد بطارية'

class Radios(QObject):
 changed=Signal()
 def __init__(self,desktop):
  super().__init__(desktop);self.desktop=desktop;self.pending=[];self.busy=False
  self.wifi='غير معروف';self.bluetooth='غير معروف';self.networks=[];self.devices=[]
  self.timer=QTimer(self);self.timer.timeout.connect(self.refresh);self.timer.start(15000)
  self.refresh()
 def run(self,args,done):
  self.pending.append((args,done));self.next()
 def next(self):
  if self.busy or not self.pending:return
  args,done=self.pending.pop(0)
  if not shutil.which(args[0]):done(False,'الأداة غير متوفرة');self.next();return
  self.busy=True;p=QProcess(self);self.process=p
  env=p.processEnvironment();env=__import__('PySide6.QtCore',fromlist=['QProcessEnvironment']).QProcessEnvironment.systemEnvironment();env.insert('LC_ALL','C');p.setProcessEnvironment(env)
  timeout=QTimer(p);timeout.setSingleShot(True);timeout.timeout.connect(p.kill)
  def finish(code,status):
   timeout.stop();out=bytes(p.readAllStandardOutput()).decode(errors='replace');err=bytes(p.readAllStandardError()).decode(errors='replace')
   self.busy=False;done(code==0,out if code==0 else err or 'تعذر تنفيذ العملية');p.deleteLater();self.next()
  p.finished.connect(finish);p.start(args[0],args[1:]);timeout.start(12000)
 def refresh(self):
  if self.busy or self.pending:return
  def wifi(ok,out):
   rows=[fields(x) for x in out.splitlines()] if ok else []
   connected=[x for x in rows if len(x)>=3 and x[0]=='wifi' and x[1]=='connected']
   self.wifi=connected[0][2] if connected else 'غير متصل' if ok else 'غير متوفر';self.changed.emit()
  def bluetooth(ok,out):
   self.bluetooth='مفعّل' if ok and 'Powered: yes' in out else 'متوقف' if ok else 'غير متوفر';self.changed.emit()
  self.run(['nmcli','-t','-f','TYPE,STATE,CONNECTION','device'],wifi)
  self.run(['bluetoothctl','show'],bluetooth)
 def show(self,kind):
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
   refresh.setEnabled(True);listing.clear()
   if not ok:status.setText(out);return
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
   if kind=='wifi':
    self.run(['nmcli','-t','-f','IN-USE,SSID,SIGNAL,SECURITY','device','wifi','list','--rescan','yes'],result)
   else:
    def known(ok,out):
     if not ok:result(False,out);return
     self.run(['bluetoothctl','devices','Connected'],lambda ok2,out2:result(True,out+'\n---connected---\n'+(out2 if ok2 else '')))
    self.run(['bluetoothctl','devices'],known)
  refresh.clicked.connect(scan);d.show();scan()
