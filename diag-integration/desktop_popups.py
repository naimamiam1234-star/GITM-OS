"""Anchored status popups backed by NetworkManager, BlueZ and PipeWire."""
import time
from PySide6.QtCore import Qt,QPoint,QSize,QTimer,QObject,QEvent
from PySide6.QtGui import QPainter,QPainterPath,QColor,QPen
from PySide6.QtWidgets import QApplication,QDialog,QVBoxLayout,QHBoxLayout,QGridLayout,QLabel,QPushButton,QSlider,QListWidget,QListWidgetItem,QLineEdit
from desktop_radios import fields,battery_info

class StatusPopup(QDialog):
 def __init__(self,owner,key):
  super().__init__(owner.desktop,Qt.Popup|Qt.FramelessWindowHint)
  self.owner=owner;self.key=key;self.setWindowTitle('GITM '+key)
  self.setAttribute(Qt.WA_TranslucentBackground);self.setLayoutDirection(Qt.RightToLeft)
  self.setFixedWidth(380);self.body=QVBoxLayout(self);self.body.setContentsMargins(22,20,22,20);self.body.setSpacing(12)
  self.status=None;self.sync=None
 def paintEvent(self,event):
  p=QPainter(self);p.setRenderHint(QPainter.Antialiasing)
  light=self.owner.desktop.appearance['mode']=='light'
  p.setBrush(QColor('#f3f6fc' if light else '#102238'));p.setPen(QPen(QColor('#aebed2' if light else '#39526f'),1))
  p.drawRoundedRect(self.rect().adjusted(1,1,-1,-1),20,20)
 def hideEvent(self,event):
  super().hideEvent(event)
  if not getattr(self.owner,'closing',False):self.last_hide=time.monotonic()
  if self.key=='control':self.owner.desktop.status_buttons['chevron'].setChecked(False)
 def keyPressEvent(self,event):
  if event.key()==Qt.Key_Escape:self.hide();return
  super().keyPressEvent(event)

class Popups(QObject):
 def __init__(self,desktop):
  super().__init__(desktop)
  self.desktop=desktop;self.panels={};self.current=None
  QApplication.instance().installEventFilter(self)
  self.control=self.create('control','مركز التحكم');self.build_control(self.control)
 def eventFilter(self,receiver,event):
  # X11 does not replay every outside popup click to the desktop below it.
  # Route status-bar presses explicitly, while leaving ordinary outside clicks to Qt.
  if event.type()!=QEvent.MouseButtonPress:return False
  active=QApplication.activePopupWidget()
  if not isinstance(active,StatusPopup) or active.owner is not self:return False
  point=event.globalPosition().toPoint()
  if active.geometry().contains(point):return False
  anchors=[(key,self.desktop.status_buttons[key]) for key in ('volume','wifi','bluetooth')]
  anchors += [('power',self.desktop.status_buttons['battery']),('control',self.desktop.status_buttons['chevron']),('power',self.desktop.power_button)]
  for key,anchor in anchors:
   local=anchor.mapFromGlobal(point)
   if not anchor.rect().contains(local):continue
   same=active.key==key;self.close()
   if not same:QTimer.singleShot(0,lambda k=key,a=anchor:self.show(k,a,toggle=False))
   return True
  return False
 def create(self,key,title):
  p=StatusPopup(self,key);self.panels[key]=p
  h=QHBoxLayout();label=QLabel(title);label.setAlignment(Qt.AlignRight|Qt.AlignVCenter);label.setStyleSheet('font-size:21px;font-weight:bold');h.addWidget(label,1)
  close=QPushButton('×');close.setFixedSize(40,40);close.setAccessibleName('إغلاق');close.clicked.connect(p.hide);h.addWidget(close);p.body.addLayout(h)
  return p
 def message(self,p,text=''):
  label=QLabel(text);label.setWordWrap(True);label.setObjectName('muted');p.body.addWidget(label);p.status=label;return label
 def button(self,p,label,fn,icon=None):
  b=QPushButton(label);b.setMinimumHeight(44);b.setAccessibleName(label)
  if icon:b.setIcon(self.desktop.icon(icon));b.setIconSize(QSize(24,24))
  b.clicked.connect(fn);p.body.addWidget(b);return b
 def close(self):
  self.closing=True
  try:
   for p in self.panels.values():p.hide()
  finally:self.closing=False
  self.current=None
 def place(self,p,anchor):
  area=anchor.screen().availableGeometry();p.adjustSize()
  size=p.size();point=anchor.mapToGlobal(QPoint(anchor.width(),anchor.height()+8))
  x=max(area.left()+8,min(point.x()-size.width(),area.right()-size.width()-8))
  y=max(area.top()+8,min(point.y(),area.bottom()-size.height()-8))
  p.move(x,y)
 def show(self,key,anchor=None,toggle=True):
  p=self.panels.get(key)
  if p and p.isVisible() and toggle:p.hide();self.current=None;return p
  if p and toggle and time.monotonic()-getattr(p,'last_hide',0)<.15:return p
  if key=='power' and p and not p.isVisible() and getattr(p,'confirm_action',None):
   self.panels.pop(key);p.deleteLater();p=None
  self.close()
  if not p:
   p=self.create(key,{'wifi':'Wi-Fi','bluetooth':'Bluetooth','volume':'الصوت','power':'الطاقة'}[key])
   getattr(self,'build_'+key)(p)
  self.current=key
  from gitm_desktop import STYLE
  p.setStyleSheet(self.desktop.theme_css(STYLE)+'\nQDialog{background:transparent;} QListWidget{background:transparent;border:0;} QListWidget::item{padding:12px;border-radius:10px;} QListWidget::item:selected{background:#278aff;color:white;} QPushButton:focus{border:2px solid #278aff;}')
  if p.sync:p.sync()
  self.place(p,anchor or (self.desktop.status_buttons['chevron'] if key=='control' else self.desktop.power_button if key=='power' else self.desktop.status_buttons[key]))
  p.show();p.raise_();p.activateWindow()
  if key=='control':self.desktop.status_buttons['chevron'].setChecked(True)
  if key in ('wifi','bluetooth'):p.scan(False)
  return p
 def command(self,p,args,success,refresh=True):
  self.message_text(p,'جارٍ التنفيذ…')
  def done(ok,out):
   self.message_text(p,success if ok else 'تعذر التنفيذ: '+out.strip()[:180])
   if refresh:self.desktop.radios.refresh()
  self.desktop.radios.run(args,done)
 def message_text(self,p,text):
  if p.status:p.status.setText(text)
 def native(self,key,args):
  self.close();self.desktop.launch(key,args)
 def build_volume(self,p):
  self.message(p)
  slider=QSlider(Qt.Horizontal);slider.setLayoutDirection(Qt.LeftToRight);slider.setRange(0,100);slider.setAccessibleName('مستوى الصوت');p.body.addWidget(slider)
  value=QLabel();p.body.addWidget(value);slider.valueChanged.connect(lambda n:value.setText(str(n)+'%'))
  slider.sliderReleased.connect(lambda:self.command(p,['pactl','set-sink-volume','@DEFAULT_SINK@',str(slider.value())+'%'],'تم تغيير مستوى الصوت'))
  mute=self.button(p,'كتم الصوت',lambda:self.command(p,['pactl','set-sink-mute','@DEFAULT_SINK@','toggle'],'تم تغيير حالة الكتم'),'volume')
  self.button(p,'كل إعدادات الصوت',lambda:self.native('audio',['pavucontrol']))
  def sync():
   state=self.desktop.radios.audio_state;available=state.get('kind')=='on'
   slider.setEnabled(available);mute.setEnabled(available)
   if not slider.isSliderDown():slider.setValue(min(100,state.get('percent',0)))
   mute.setText('إلغاء الكتم' if state.get('mute') else 'كتم الصوت')
   self.message_text(p,'الصوت مكتوم' if state.get('mute') else 'مخرج الصوت الافتراضي' if available else 'لا يوجد مخرج صوت متاح')
  p.sync=sync
 def build_radio(self,p,kind):
  toggle=self.button(p,'',lambda:self.radio_power(p,kind))
  self.message(p)
  search=QLineEdit();search.setPlaceholderText('بحث في القائمة…');p.body.addWidget(search)
  listing=QListWidget();listing.setFixedHeight(180);listing.setAccessibleName('الشبكات' if kind=='wifi' else 'أجهزة Bluetooth');p.body.addWidget(listing)
  def filter_rows(text):
   for i in range(listing.count()):listing.item(i).setHidden(text.casefold() not in listing.item(i).text().casefold())
  search.textChanged.connect(filter_rows)
  password=QLineEdit();password.setEchoMode(QLineEdit.Password);password.setPlaceholderText('كلمة مرور الشبكة، عند الحاجة');password.setAccessibleName('كلمة مرور Wi-Fi')
  if kind=='wifi':p.body.addWidget(password)
  def connect():
   item=listing.currentItem()
   if not item or not item.data(Qt.UserRole):self.message_text(p,'اختر عنصرًا من القائمة أولًا');return
   address,connected=item.data(Qt.UserRole)
   if kind=='wifi':
    args=['nmcli','--wait','8','device','wifi','connect',address]
    if password.text():args+=['password',password.text()]
    self.command(p,args,'تم الاتصال بالشبكة');password.clear()
   else:self.command(p,['bluetoothctl','--timeout','8','disconnect' if connected else 'connect',address],'تم فصل الجهاز' if connected else 'تم الاتصال بالجهاز')
  action=self.button(p,'اتصال',connect)
  refresh=self.button(p,'بحث / تحديث',lambda:p.scan(True),'sync')
  self.button(p,'كل إعدادات '+('الشبكة' if kind=='wifi' else 'Bluetooth'),lambda:self.native('settings',['systemsettings','kcm_networkmanagement' if kind=='wifi' else 'kcm_bluetooth']))
  def sync():
   state=self.desktop.radios.wifi_state if kind=='wifi' else self.desktop.radios.bluetooth_state
   enabled=state['kind'] in ('on','connected');available=state['kind'] not in ('missing','unknown','error')
   toggle.setText(('إيقاف ' if enabled else 'تفعيل ')+('Wi-Fi' if kind=='wifi' else 'Bluetooth'));toggle.setEnabled(available);refresh.setEnabled(available and enabled);action.setEnabled(available and enabled)
   for widget in (search,listing,action,refresh):widget.setVisible(available and enabled)
   if kind=='wifi':password.setVisible(available and enabled)
   if state['kind'] in ('missing','off','error'):self.message_text(p,'لا يوجد محول متاح' if state['kind']=='missing' else 'الاتصال متوقف' if state['kind']=='off' else 'تعذرت قراءة خدمة الاتصال')
  def result(ok,out):
   if not p.isVisible():return
   refresh.setEnabled(True);listing.clear()
   if not ok:self.message_text(p,'تعذر قراءة الأجهزة: '+out.strip()[:160]);return
   if kind=='wifi':
    for row in map(fields,out.splitlines()):
     if len(row)<4 or not row[1]:continue
     active,ssid,signal,security=row[:4];item=QListWidgetItem(('متصل · ' if active=='*' else '')+ssid+' · '+signal+'%'+(' · مقفلة' if security and security!='--' else ''))
     item.setData(Qt.UserRole,(ssid,active=='*'));listing.addItem(item)
   else:
    known,_,connected=out.partition('\n---connected---\n');active={line.split()[1] for line in connected.splitlines() if line.startswith('Device ') and len(line.split())>=2}
    for line in known.splitlines():
     row=line.split(' ',2)
     if len(row)!=3 or row[0]!='Device':continue
     item=QListWidgetItem(('متصل · ' if row[1] in active else '')+row[2]);item.setData(Qt.UserRole,(row[1],row[1] in active));listing.addItem(item)
   self.message_text(p,('الشبكة الحالية: '+self.desktop.radios.wifi if kind=='wifi' else 'الأجهزة المعروفة · لإقران جهاز جديد افتح كل الإعدادات') if listing.count() else 'لا توجد نتائج متاحة')
   filter_rows(search.text());sync()
  def scan(discover):
   sync();state=self.desktop.radios.wifi_state if kind=='wifi' else self.desktop.radios.bluetooth_state
   if state['kind'] in ('missing','off','unknown','error'):
    listing.clear();self.message_text(p,('لا يوجد محول متاح' if state['kind']=='missing' else 'الاتصال متوقف' if state['kind']=='off' else 'جارٍ قراءة خدمة الاتصال' if state['kind']=='unknown' else 'تعذرت قراءة خدمة الاتصال'));return
   refresh.setEnabled(False);self.message_text(p,'جارٍ البحث…')
   if kind=='wifi':self.desktop.radios.run(['nmcli','--wait','8','-t','-f','IN-USE,SSID,SIGNAL,SECURITY','device','wifi','list','--rescan','yes' if discover else 'no'],result)
   else:
    def known(ok,out):
     if not ok:result(False,out);return
     self.desktop.radios.run(['bluetoothctl','--timeout','2','devices','Connected'],lambda ok2,out2:result(ok2,out+'\n---connected---\n'+out2))
    def read_known():self.desktop.radios.run(['bluetoothctl','--timeout','2','devices'],known)
    if discover:self.desktop.radios.run(['bluetoothctl','--timeout','4','scan','on'],lambda ok,out:read_known() if ok else result(False,out))
    else:read_known()
  listing.currentItemChanged.connect(lambda current,previous:action.setText('قطع الاتصال' if kind=='bluetooth' and current and current.data(Qt.UserRole) and current.data(Qt.UserRole)[1] else 'اتصال'))
  p.sync=sync;p.scan=scan
 def build_wifi(self,p):self.build_radio(p,'wifi')
 def build_bluetooth(self,p):self.build_radio(p,'bluetooth')
 def radio_power(self,p,kind):
  state=self.desktop.radios.wifi_state if kind=='wifi' else self.desktop.radios.bluetooth_state
  enable=state['kind'] not in ('on','connected')
  args=['nmcli','radio','wifi','on' if enable else 'off'] if kind=='wifi' else ['bluetoothctl','--timeout','2','power','on' if enable else 'off']
  self.command(p,args,'تم تغيير حالة الاتصال')
 def build_power(self,p):
  info=battery_info();self.message(p,info['text'] if info['present'] else 'الجهاز لا يحتوي على بطارية متاحة')
  for label,action,icon in [('تعليق الجهاز','suspend','suspend'),('إعادة التشغيل','reboot','reboot'),('إيقاف التشغيل','poweroff','power')]:
   self.button(p,label,lambda checked=False,a=action:self.confirm_power(a),icon)
 def confirm_power(self,action):
  self.show('power',toggle=False);p=self.panels['power']
  p.confirm_action=action
  while p.body.count()>1:
   item=p.body.takeAt(1)
   if item.widget():item.widget().deleteLater()
  label={'suspend':'تعليق الجهاز','reboot':'إعادة التشغيل','poweroff':'إيقاف التشغيل'}[action]
  self.message(p,label+'؟ احفظ عملك قبل المتابعة.')
  cancel=self.button(p,'إلغاء',self.reset_power)
  self.button(p,'تأكيد '+label,lambda:self.execute_power(action),'power')
  cancel.setFocus();self.place(p,self.desktop.power_button)
 def reset_power(self):
  p=self.panels.pop('power');p.hide();p.deleteLater();self.show('power',toggle=False)
 def execute_power(self,action):
  self.close();self.desktop.launch('power',['systemctl',action])
 def build_control(self,p):
  grid=QGridLayout();p.body.addLayout(grid);self.tiles={}
  actions=[('wifi','Wi-Fi',lambda:self.show('wifi')),('bluetooth','Bluetooth',lambda:self.show('bluetooth')),('airplane','وضع الطيران',self.airplane),('settings','الوضع الليلي',self.mode),('camera','لقطة شاشة',lambda:self.native('screenshot',['spectacle'])),('lock','قفل الشاشة',lambda:self.native('lock',['loginctl','lock-session'])),('volume','الصوت',lambda:self.show('volume')),('power','الطاقة',lambda:self.show('power'))]
  for i,(key,label,fn) in enumerate(actions):
   b=QPushButton(label);b.setMinimumHeight(56);b.setIcon(self.desktop.icon(key));b.setIconSize(QSize(24,24));b.setStyleSheet('font-size:14px;padding:6px;border-radius:14px');b.clicked.connect(fn);b.setAccessibleName(label);grid.addWidget(b,i//2,i%2);self.tiles[key]=b
  p.body.addWidget(QLabel('السطوع'))
  self.desktop.brightness=QSlider(Qt.Horizontal);self.desktop.brightness.setLayoutDirection(Qt.LeftToRight);self.desktop.brightness.setRange(5,100);self.desktop.brightness.setValue(70);self.desktop.brightness.setAccessibleName('السطوع')
  import system_settings
  available=bool(system_settings.brightness_devices());self.desktop.brightness.setEnabled(available);self.desktop.brightness.setToolTip('السطوع' if available else 'العتاد لا يوفر تحكمًا بالسطوع')
  if not available:self.desktop.brightness.setValue(5)
  self.desktop.brightness.sliderReleased.connect(self.desktop.apply_brightness);p.body.addWidget(self.desktop.brightness)
  if not available:
   hint=QLabel('السطوع غير متاح على هذه الشاشة');hint.setObjectName('muted');p.body.addWidget(hint)
  p.body.addWidget(QLabel('مستوى الصوت'))
  volume=QSlider(Qt.Horizontal);volume.setLayoutDirection(Qt.LeftToRight);volume.setRange(0,100);volume.setAccessibleName('مستوى الصوت');p.body.addWidget(volume)
  volume.sliderReleased.connect(lambda:self.command(p,['pactl','set-sink-volume','@DEFAULT_SINK@',str(volume.value())+'%'],'تم تغيير مستوى الصوت'))
  self.message(p);self.button(p,'خلفيات وإقلاع GITM',self.desktop.choose_wallpapers,'camera');self.button(p,'كل الإعدادات',self.desktop.settings,'settings')
  def sync():
   from desktop_radios import state_icon
   light=self.desktop.appearance['mode']=='light'
   for key in ('settings','camera','lock','power','airplane'):self.tiles[key].setIcon(self.desktop.icon(key))
   for key,state in [('wifi',self.desktop.radios.wifi_state),('bluetooth',self.desktop.radios.bluetooth_state)]:
    on=state['kind'] in ('on','connected');self.tiles[key].setText(('Wi-Fi' if key=='wifi' else 'Bluetooth')+'\n'+('متصل' if state['kind']=='connected' else 'مفعّل' if on else 'غير متاح' if state['kind']=='missing' else 'متوقف' if state['kind']=='off' else 'جارٍ القراءة'))
    self.tiles[key].setIcon(state_icon(key,dict(state,light=light)))
    self.tiles[key].setStyleSheet('font-size:14px;padding:6px;border-radius:14px;'+('background:#166aba;color:white;border:1px solid #459cff' if on else ''))
   self.tiles['settings'].setText('الوضع النهاري' if light else 'الوضع الليلي')
   off=all(s['kind'] in ('off','missing') for s in [self.desktop.radios.wifi_state,self.desktop.radios.bluetooth_state])
   self.tiles['airplane'].setText('وضع الطيران\n'+('الاتصالات متوقفة' if off else 'الاتصالات متاحة'))
   self.tiles['airplane'].setEnabled(any(s['kind'] in ('on','connected','off') for s in [self.desktop.radios.wifi_state,self.desktop.radios.bluetooth_state]))
   audio=self.desktop.radios.audio_state;volume.setEnabled(audio.get('kind')=='on');self.tiles['volume'].setIcon(state_icon('volume',dict(audio,light=light)))
   if not volume.isSliderDown():volume.setValue(min(100,audio.get('percent',0)))
  p.sync=sync
 def mode(self):
  self.desktop.appearance['mode']='light' if self.desktop.appearance['mode']=='dark' else 'dark';self.desktop.save_appearance();self.show('control',toggle=False)
 def airplane(self):
  p=self.control;states=[self.desktop.radios.wifi_state,self.desktop.radios.bluetooth_state];enable=not all(s['kind'] in ('off','missing') for s in states)
  args=['nmcli','radio','all','off' if enable else 'on']
  def done(ok,out):
   if not ok:self.message_text(p,'تعذر تغيير Wi-Fi: '+out[:120]);return
   if self.desktop.radios.bluetooth_state['kind']=='missing':self.desktop.radios.refresh();return
   self.command(p,['bluetoothctl','--timeout','2','power','off' if enable else 'on'],'تم تحديث الاتصالات اللاسلكية')
  self.desktop.radios.run(args,done)
 def refresh(self):
  for p in self.panels.values():
   if p.isVisible() and p.sync:p.sync();p.update()
