"""Explicit adapter operations; inventory never opens a diagnostic channel."""
import json
from shiboken6 import isValid
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QLineEdit,QComboBox,QLabel,QTableWidget,QTableWidgetItem,QTextEdit,QGroupBox
import transport
from diagnostic_workspace import Worker
from professional_components import triple,InfoCard,MetricCard,action_button,configure_table

def text(ar,fr,en):return triple(ar,fr,en)
class Workspace(QWidget):
 def __init__(self,window):
  super().__init__();self.window=window;self.worker=None;self.actions=[]
  root=QVBoxLayout(self);row=QHBoxLayout();root.addLayout(row)
  for title,hint in [('USB','/dev/ttyUSB0 · /dev/ttyACM0'),('Bluetooth','BlueZ · /dev/rfcomm0'),('Wi-Fi / TCP','host:port')]:
   card=InfoCard(title);card.body.addWidget(QLabel(hint));row.addWidget(card)
  form=QFormLayout();root.addLayout(form);self.kind=QComboBox()
  for label,key in [('USB','usb'),('Bluetooth Classic','bluetooth'),('Wi-Fi / TCP','wifi'),('RFCOMM (advanced)','rfcomm'),('BLE (advanced)','ble')]:self.kind.addItem(label,key)
  self.target=QLineEdit();self.target.setPlaceholderText('/dev/ttyUSB0 · host:port · MAC:channel');self.baud=QComboBox();self.baud.addItems(['115200','38400','9600']);self.family=QComboBox();self.family.addItems(['auto','elm','gitm'])
  for label,widget in [(text('النقل','Transport','Transport'),self.kind),(text('العنوان','Adresse','Endpoint'),self.target),(text('سرعة الاتصال','Débit série','Serial baud'),self.baud),(text('عائلة المحول','Famille','Adapter family'),self.family)]:form.addRow(label,widget)
  line=QHBoxLayout();root.addLayout(line)
  for label,fn in [(text('الأجهزة','Inventaire','Refresh devices'),self.refresh_inventory),(text('اتصال','Connecter','Connect'),self.connect_adapter),(text('فصل','Déconnecter','Disconnect'),self.disconnect_adapter),(text('اختبار الهوية','Tester identité','Test identity'),self.test_identity),(text('اكتشاف معروف','Détecter connu','Discover known'),self.discover)]:
   button=action_button(label);button.clicked.connect(fn);line.addWidget(button);self.actions.append(button)
  self.status=QLabel();root.addWidget(self.status);self.identity=MetricCard(text('هوية المحول','Identité','Adapter identity'));root.addWidget(self.identity)
  self.inventory=QTableWidget(0,4);self.inventory.setHorizontalHeaderLabels([text('جهاز','Appareil','Device'),text('منفذ','Port','Port'),text('هوية','Identité','Identity'),text('دليل','Preuve','Evidence')]);configure_table(self.inventory);root.addWidget(self.inventory,1);self.inventory.cellClicked.connect(self.select_device);self.devices=[]
  self.log=QTextEdit();self.log.setReadOnly(True);self.log.setMaximumHeight(110);root.addWidget(self.log)
  details=QGroupBox(text('تفاصيل تقنية','Détails techniques','Technical details'));details.setCheckable(True);details.setChecked(False);dl=QVBoxLayout(details);self.raw=QTextEdit();self.raw.setReadOnly(True);self.raw.setMaximumHeight(130);self.raw.hide();dl.addWidget(self.raw);details.toggled.connect(self.raw.setVisible);root.addWidget(details);self.refresh_state()
 def launch(self,fn,done):
  if any(getattr(self.window,k,None) is not None for k in ('diagnostic_worker','_obd_worker')) or (getattr(self.window,'task',None) is not None and self.window.task.isRunning()):
   self.status.setText(text('طلب جارٍ','Opération en cours','Operation in progress'));return
  self.worker=Worker(fn,self.window);worker=self.worker;self.window.diagnostic_worker=worker;self.window._obd_worker=worker
  for b in self.actions:b.setEnabled(False)
  worker.result.connect(lambda r:done(r) if isValid(self) and not worker.cancel.is_set() else None);worker.failure.connect(lambda e:self.error(e) if isValid(self) and not worker.cancel.is_set() else None)
  def finished():
   if getattr(self.window,'diagnostic_worker',None) is worker:self.window.diagnostic_worker=None
   if getattr(self.window,'_obd_worker',None) is worker:self.window._obd_worker=None
   if isValid(self):
    self.worker=None
    for b in self.actions:b.setEnabled(True)
    self.refresh_state()
  worker.finished.connect(finished);worker.start()
 def error(self,error):self.status.setText(str(error));self.log.append(str(error))
 def refresh_state(self):
  info=transport.LINK.info();self.identity.set_value(info.get('adapter') or '—',str(info.get('target') or '—'));self.status.setText(text('متصل','Connecté','Connected') if info.get('connected') else text('غير متصل','Déconnecté','Disconnected'))
 def result(self,result):self.raw.setPlainText(json.dumps(result,ensure_ascii=False,indent=2));self.log.append(json.dumps(result,ensure_ascii=False));self.refresh_state()
 def refresh_inventory(self):self.launch(lambda c,p:transport.inventory(),self.show_inventory)
 def show_inventory(self,data):
  self.devices=data.get('devices',[]);self.inventory.setRowCount(len(self.devices))
  for row,d in enumerate(self.devices):
   ident=d.get('identification',{});values=[d.get('product') or d.get('name') or d.get('type','—'),', '.join(d.get('ports',[])) or d.get('path','—'),ident.get('name','—'),ident.get('evidence') or ident.get('confidence','—')]
   for col,value in enumerate(values):self.inventory.setItem(row,col,QTableWidgetItem(str(value)))
  self.result(data)
  if data.get('errors'):self.error('; '.join(data['errors']))
 def select_device(self,row,col):
  d=self.devices[row];ports=d.get('ports',[])
  if ports:self.target.setText(ports[0]);self.kind.setCurrentIndex(self.kind.findData('bluetooth' if ports[0].startswith('/dev/rfcomm') else 'usb'))
  elif d.get('type')=='bluetooth_paired':self.target.setText(d.get('path','')+':1');self.kind.setCurrentIndex(self.kind.findData('rfcomm'))
 def connect_adapter(self):
  args=(self.kind.currentData(),self.target.text().strip(),int(self.baud.currentText()),self.family.currentText());self.launch(lambda c,p:transport.LINK.connect(*args),self.result)
 def disconnect_adapter(self):self.launch(lambda c,p:(transport.LINK.close(),transport.LINK.info())[1],self.result)
 def discover(self):self.launch(lambda c,p:transport.LINK.discover(),self.result)
 def test_identity(self):
  info=transport.LINK.info()
  if not info.get('connected'):self.error(text('اتصل بمحول معروف أولاً','Connecter un adaptateur connu','Connect a known adapter first'));return
  command='ATI' if info.get('adapter')=='elm' else 'GITM_HELLO';self.launch(lambda c,p:{'identity_response':transport.LINK.query(command)},self.result)
 def hideEvent(self,event):
  if self.worker:self.worker.cancel.set()
  super().hideEvent(event)
def show(window):
 layout=window.page(text('المحول والاتصال','Adaptateur et connexion','VCI and connection'));page=Workspace(window);layout.addWidget(page);return page
