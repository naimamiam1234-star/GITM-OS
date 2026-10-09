"""GITM desktop session. Native Linux launchers; no simulated vehicle data."""
import os
import sys
import shutil
import datetime
from pathlib import Path
from PySide6.QtCore import Qt, QSize, QTimer, QProcess, QIODevice, QRectF, QRect, QPoint
from PySide6.QtGui import QIcon, QFontDatabase, QPainter, QColor, QLinearGradient, QPainterPath, QPixmap, QPen
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
 QGridLayout, QLabel, QPushButton, QLineEdit, QFrame, QDialog, QMessageBox, QScrollArea, QSlider, QProgressBar, QFileDialog, QLayout, QSizePolicy)

ROOT = Path(__file__).resolve().parent
STATE = Path(os.environ.get('GITM_STATE', str(Path.home()/'.local/share/gitm')))
APPS = [
 ('autodiag','GITM AutoDiag','تشخيص السيارات','engine',None),
 ('files','الملفات','المجلدات والمستندات','files',['dolphin']),
 ('browser','المتصفح','الإنترنت والمراجع','browser',['falkon']),
 ('settings','الإعدادات','الشبكة والشاشة والصوت','settings',None),
 ('updates','التحديثات','النظام وبرنامج التشخيص','update',None),
 ('photos','الصور','مكتبة الصور','camera',['gwenview']),
 ('media','الوسائط','الموسيقى والفيديو','music',['vlc']),
 ('calculator','الحاسبة','حساباتك اليومية','calculator',['kcalc']),
 ('install','تثبيت GITM OS','التثبيت على القرص','update',['gitm-install']),
 ('documents','المستندات','قراءة ملفات PDF','reports',['okular']),
]
STYLE = '''
QWidget{color:#f0f5ff;font-family:Tajawal;font-size:17px;background:transparent;}
QLabel#title{font-size:43px;font-weight:bold;} QLabel#muted{color:#b6c5de;font-size:16px;}
QPushButton{background:rgba(22,39,62,195);border:1px solid #36485f;border-radius:12px;padding:10px;}
QPushButton:hover{background:rgba(42,74,110,225);border-color:#449eff;}
QPushButton:pressed{background:#12518c;} QPushButton:disabled{color:#77859a;}
QPushButton#appIcon,QPushButton#dockIcon{background:transparent;border:0;padding:0;}
QPushButton#appIcon:hover,QPushButton#dockIcon:hover{background:rgba(180,211,255,25);border:1px solid rgba(170,210,255,60);}
QPushButton#nav{background:transparent;border:0;color:#bccde7;padding:4px 12px;}
QPushButton#radio{background:rgba(20,39,61,200);border:1px solid #39526f;border-radius:30px;padding:0;}
QPushButton#radio:hover{background:#0d7cf6;}
QLineEdit{background:rgba(13,26,45,215);border:1px solid #425572;border-radius:24px;padding:14px 20px;}
QScrollBar:vertical{background:transparent;width:7px;} QScrollBar::handle:vertical{background:#455771;border-radius:3px;min-height:20px;}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}
QProgressBar{background:#243246;border:0;border-radius:5px;}QProgressBar::chunk{background:#2e93ff;border-radius:5px;}
QSlider::groove:horizontal{height:7px;background:#2c3d51;border-radius:3px;}
QSlider::sub-page:horizontal{background:#278aff;border-radius:3px;}
QSlider::handle:horizontal{width:18px;margin:-5px 0;background:white;border-radius:9px;}
QDialog,QMessageBox{background:#102238;}QToolTip{background:#132941;color:white;padding:8px;}
'''


class GlassPanel(QFrame):
 def __init__(self,desktop,parent=None):
  super().__init__(parent);self.desktop=desktop
 def paintEvent(self,event):
  p=QPainter(self);p.setRenderHint(QPainter.Antialiasing)
  bounds=QRectF(self.rect()).adjusted(.5,.5,-.5,-.5)
  clip=QPainterPath();clip.addRoundedRect(bounds,22,22);p.setClipPath(clip)
  if not self.desktop.blurred.isNull():
   pos=self.mapTo(self.desktop,QPoint(0,0));p.drawPixmap(self.rect(),self.desktop.blurred,QRect(pos,self.size()))
  gradient=QLinearGradient(0,0,self.width(),self.height());gradient.setColorAt(0,QColor(16,29,47,218));gradient.setColorAt(1,QColor(8,17,28,227));p.fillRect(self.rect(),gradient)
  p.setClipping(False);p.setPen(QPen(QColor(158,188,219,65),1));p.drawRoundedRect(bounds,22,22)

class Desktop(QWidget):
 def __init__(self):
  super().__init__()
  self.setWindowTitle('GITM OS 3.3 · Desktop')
  self.setWindowFlags(Qt.Window|Qt.FramelessWindowHint|Qt.WindowStaysOnBottomHint)
  self.resize(1440,900);self.processes={};self.dialogs=[];self.tiles=[]
  self.wallpaper=QPixmap(str(ROOT/'assets/desktop/wallpaper.png'));self.background=QPixmap();self.blurred=QPixmap()
  try:
   personal=QPixmap((STATE/'wallpaper-path.txt').read_text().strip())
   if not personal.isNull():self.wallpaper=personal
  except OSError:pass
  for f in (ROOT/'assets').glob('Tajawal-*.ttf'):QFontDatabase.addApplicationFont(str(f))
  self.setLayoutDirection(Qt.LeftToRight);self.setStyleSheet(STYLE)
  outer=QVBoxLayout(self);outer.setSizeConstraint(QLayout.SetNoConstraint);outer.setContentsMargins(42,24,42,20);outer.setSpacing(22)
  top=QHBoxLayout();logo=QLabel('G');logo.setStyleSheet('color:#159bff;font-size:33px;font-family:DejaVu Sans;font-weight:900');top.addWidget(logo)
  brand=QLabel('GITM OS');brand.setStyleSheet('font-size:21px;font-family:DejaVu Sans');top.addWidget(brand);top.addSpacing(18)
  for title,fn in [('الرئيسية',lambda:self.search.clear()),('التطبيقات',lambda:self.search.setFocus()),('النظام',self.settings)]:
   b=QPushButton(title);b.setObjectName('nav');b.clicked.connect(fn);top.addWidget(b)
  top.addStretch()
  self.status_buttons={}
  for key,title,fn in [('wifi','Wi-Fi',lambda:self.radios.show('wifi')),('bluetooth','Bluetooth',lambda:self.radios.show('bluetooth')),('battery','البطارية',self.power),('sync','تحديث الحالة',lambda:self.radios.refresh()),('search','بحث',lambda:self.search.setFocus()),('chevron','مركز التحكم',self.toggle_control)]:
   b=QPushButton();b.setIcon(self.icon(key));b.setIconSize(QSize(24,24));b.setFixedSize(42,40);b.setObjectName('nav');b.setToolTip(title);b.setAccessibleName(title);b.clicked.connect(fn);top.addWidget(b);self.status_buttons[key]=b
  self.status_buttons['chevron'].setCheckable(True)
  self.battery_label=QLabel();self.battery_label.setStyleSheet('font-size:13px');top.addWidget(self.battery_label)
  self.clock=QLabel();self.clock.setStyleSheet('font-size:15px');top.addWidget(self.clock)
  power=QPushButton();power.setIcon(self.icon('power'));power.setIconSize(QSize(24,24));power.setToolTip('الطاقة');power.setObjectName('nav');power.clicked.connect(self.power);top.addWidget(power);outer.addLayout(top)
  content=QHBoxLayout();content.setSpacing(28)
  left=QVBoxLayout();left.setSpacing(18);content.addLayout(left,1)
  welcome=QHBoxLayout();words=QVBoxLayout();heading=QLabel('مرحبًا بك.');heading.setObjectName('title');words.addWidget(heading)
  subtitle=QLabel('كل أدواتك، في مساحة عمل واحدة.');subtitle.setObjectName('muted');words.addWidget(subtitle);welcome.addLayout(words,1)
  title=QLabel('GITM <span style="color:#248dff">OS</span><br><span style="font-size:12px;letter-spacing:3px;color:#becce1">YOUR WORKSPACE. YOUR WAY.</span>');title.setStyleSheet('font-size:40px;font-family:DejaVu Sans;font-weight:bold');title.setAlignment(Qt.AlignRight|Qt.AlignVCenter);welcome.addWidget(title);left.addLayout(welcome)
  self.search=QLineEdit();self.search.setPlaceholderText('ابحث عن تطبيق، إعدادات أو أدوات…');self.search.textChanged.connect(self.filter_apps);self.search.setLayoutDirection(Qt.RightToLeft);left.addWidget(self.search)
  scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setFrameShape(QFrame.NoFrame)
  container=QWidget();grid=QGridLayout(container);grid.setContentsMargins(0,0,0,0);grid.setSpacing(14);scroll.setWidget(container);self.app_grid=grid
  order=['autodiag','documents','photos','media','settings','files','browser','updates','calculator','install']
  for i,key in enumerate(order):
   _,name,desc,icon,command=next(a for a in APPS if a[0]==key)
   card=QWidget();v=QVBoxLayout(card);v.setContentsMargins(2,8,2,8);v.setSpacing(7);v.setAlignment(Qt.AlignCenter)
   b=QPushButton();b.setObjectName('appIcon');b.setIcon(self.icon(icon));b.setIconSize(QSize(80,80));b.setFixedSize(88,88);b.setToolTip(name);b.setAccessibleName(name);b.clicked.connect(lambda checked=False,k=key:self.activate(k));v.addWidget(b,0,Qt.AlignHCenter)
   label=QLabel(name);label.setAlignment(Qt.AlignCenter);label.setStyleSheet('font-weight:bold;font-size:18px');v.addWidget(label)
   detail=QLabel(desc);detail.setWordWrap(True);detail.setAlignment(Qt.AlignCenter);detail.setStyleSheet('color:#b3c4db;font-size:14px');v.addWidget(detail)
   grid.addWidget(card,i//5,i%5);self.tiles.append((name+' '+desc+' '+key,card))
  left.addWidget(scroll,1)
  self.control=GlassPanel(self);self.control.setFixedWidth(355);right=QVBoxLayout(self.control);right.setContentsMargins(20,20,20,20);right.setSpacing(15)
  control_title=QLabel('مركز التحكم');control_title.setStyleSheet('font-size:17px;font-weight:bold;color:#a9bbd2');right.addWidget(control_title)
  radios=QGridLayout();right.addLayout(radios)
  for i,(title,icon,fn) in enumerate([('Wi-Fi','wifi',lambda:self.radios.show('wifi')),('Bluetooth','bluetooth',lambda:self.radios.show('bluetooth')),('المظهر','settings',self.choose_appearance),('وضع الطيران','airplane',self.toggle_airplane)]):
   v=QVBoxLayout();b=QPushButton();b.setIcon(self.icon(icon));b.setIconSize(QSize(40,40));b.setFixedSize(60,60);b.setObjectName('radio');b.clicked.connect(fn);b.setAccessibleName(title);v.addWidget(b,0,Qt.AlignCenter)
   label=QLabel(title);label.setAlignment(Qt.AlignCenter);label.setStyleSheet('font-size:13px');v.addWidget(label);radios.addLayout(v,0,i)
  right.addWidget(self.divider())
  light=QHBoxLayout();light.addWidget(QLabel('☀'));self.brightness=QSlider(Qt.Horizontal);self.brightness.setRange(5,100);self.brightness.setValue(70)
  import system_settings
  self.brightness.setEnabled(bool(system_settings.brightness_devices()));self.brightness.setToolTip('السطوع' if self.brightness.isEnabled() else 'العتاد لا يوفر تحكمًا بالسطوع');self.brightness.sliderReleased.connect(self.apply_brightness);light.addWidget(self.brightness);light.addWidget(QLabel('☀'));right.addLayout(light)
  tools=QGridLayout();right.addLayout(tools)
  for i,(label,icon,key,cmd) in enumerate([('الشاشة','display','display',['systemsettings5']),('الصوت','volume','sound',['pavucontrol']),('لوحة المفاتيح','keyboard','keyboard',['onboard']),('الطاقة','battery','power-settings',['systemsettings5'])]):
   b=QPushButton(label);b.setIcon(self.icon(icon));b.setIconSize(QSize(24,24));b.setMinimumHeight(60);b.setStyleSheet('padding:8px;font-size:13px;background:rgba(25,38,56,155);border:1px solid #344054;border-radius:12px');b.clicked.connect(lambda checked=False,k=key,c=cmd:self.launch(k,c));tools.addWidget(b,i//2,i%2)
  right.addWidget(self.divider())
  tip=QLabel('مساحة عمل جاهزة\nافتح ملفاتك وبرامجك، وانتقل إلى AutoDiag عند بدء فحص السيارة.');tip.setWordWrap(True);tip.setStyleSheet('font-size:16px;color:#bfcee1');right.addWidget(tip)
  self.settings_button=QPushButton('كل الإعدادات  ›');self.settings_button.clicked.connect(self.settings);right.addWidget(self.settings_button);right.addStretch();content.addWidget(self.control)
  self.control.hide()
  outer.addLayout(content,1)
  cards=QHBoxLayout();cards.setSpacing(20)
  intro=GlassPanel(self);il=QVBoxLayout(intro);il.setContentsMargins(22,18,22,18);il.addWidget(QLabel('GITM AutoDiag'));info=QLabel('بيئة تشخيص مستقلة\nالمحولات · المركبات · التقارير');info.setWordWrap(True);info.setObjectName('muted');il.addWidget(info)
  open_diag=QPushButton('فتح برنامج التشخيص  ›');open_diag.clicked.connect(lambda:self.activate('autodiag'));il.addWidget(open_diag);cards.addWidget(intro,1)
  quick=GlassPanel(self);ql=QVBoxLayout(quick);ql.setContentsMargins(20,18,20,18);ql.addWidget(QLabel('وصول سريع'));qr=QHBoxLayout();ql.addLayout(qr)
  for key in ['files','updates','browser']:
   item=next(a for a in APPS if a[0]==key);b=QPushButton(item[1]);b.setIcon(self.icon(item[3]));b.setIconSize(QSize(28,28));b.setMinimumHeight(75);b.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Preferred);b.clicked.connect(lambda checked=False,k=key:self.activate(k));qr.addWidget(b)
  cards.addWidget(quick,1)
  system=GlassPanel(self);sl=QVBoxLayout(system);sl.setContentsMargins(22,18,22,18);sl.setSpacing(8);sl.addWidget(QLabel('حالة النظام'));self.stat_rows={}
  for key,title in [('ram','RAM'),('disk','التخزين')]:
   row=QHBoxLayout();label=QLabel(title);label.setMinimumWidth(66);row.addWidget(label);bar=QProgressBar();bar.setRange(0,100);bar.setTextVisible(False);bar.setFixedHeight(10);row.addWidget(bar,1);value=QLabel();value.setMinimumWidth(47);row.addWidget(value);sl.addLayout(row);self.stat_rows[key]=(bar,value)
  self.stats=QLabel();self.stats.setStyleSheet('font-size:13px;color:#b5c4d9');self.stats.setWordWrap(True);sl.addWidget(self.stats);cards.addWidget(system,1);outer.addLayout(cards)
  dock=GlassPanel(self);dr=QHBoxLayout(dock);dr.setContentsMargins(15,10,15,10);dr.setSpacing(10)
  launcher=QPushButton('⠿');launcher.setObjectName('dockIcon');launcher.setStyleSheet('font-size:29px');launcher.clicked.connect(lambda:self.search.setFocus());dr.addWidget(launcher)
  for key in ['autodiag','files','browser','documents','photos','media','settings']:
   item=next(a for a in APPS if a[0]==key);b=QPushButton();b.setObjectName('dockIcon');b.setIcon(self.icon(item[3]));b.setIconSize(QSize(49,49));b.setFixedSize(56,56);b.setToolTip(item[1]);b.setAccessibleName(item[1]);b.clicked.connect(lambda checked=False,k=key:self.activate(k));dr.addWidget(b)
  outer.addWidget(dock,0,Qt.AlignHCenter)
  from desktop_radios import Radios
  self.radios=Radios(self);self.radios.changed.connect(self.refresh_radios)
  self.refresh_radios()
  self.refresh();self.timer=QTimer(self);self.timer.timeout.connect(self.refresh);self.timer.start(5000)
 def toggle_control(self):
  visible=not self.control.isVisible();self.control.setVisible(visible);self.status_buttons['chevron'].setChecked(visible)
 def refresh_radios(self):
  from desktop_radios import battery
  self.status_buttons['wifi'].setToolTip('Wi-Fi · '+self.radios.wifi)
  self.status_buttons['bluetooth'].setToolTip('Bluetooth · '+self.radios.bluetooth)
  text=battery();self.battery_label.setText(text);self.status_buttons['battery'].setToolTip(text)
  for key,value in [('wifi',self.radios.wifi),('bluetooth',self.radios.bluetooth)]:
   self.status_buttons[key].setStyleSheet('color:#56b5ff;' if value not in ('غير متصل','متوقف','غير متوفر','غير معروف') else 'color:#a0aabd;')
 def divider(self):
  line=QFrame();line.setFixedHeight(1);line.setStyleSheet('background:rgba(162,184,211,55)');return line
 def choose_appearance(self):
  d,v=self.panel('المظهر')
  note=QLabel('الخلفية الحالية مستوحاة من مرجعك. يمكنك اختيار خلفية شخصية.');note.setWordWrap(True);v.addWidget(note)
  b=QPushButton('اختيار خلفية');v.addWidget(b)
  def choose():
   path,_=QFileDialog.getOpenFileName(self,'الخلفية',str(Path.home()),'Images (*.png *.jpg *.jpeg)')
   if path:
    image=QPixmap(path)
    if not image.isNull():
     STATE.mkdir(parents=True,exist_ok=True);(STATE/'wallpaper-path.txt').write_text(path);self.wallpaper=image;self.update_background();self.update()
  b.clicked.connect(choose);d.show()
 def toggle_airplane(self):
  answer=QMessageBox.question(self,'وضع الطيران','تعطيل الاتصالات اللاسلكية؟ اختر لا لاستعادة الحالة السابقة.',QMessageBox.Yes|QMessageBox.No|QMessageBox.Cancel)
  if answer==QMessageBox.Cancel:return
  try:__import__('system_settings').radio('airplane',answer==QMessageBox.Yes)
  except Exception as e:QMessageBox.warning(self,'GITM',str(e))
 def apply_brightness(self):
  try:__import__('system_settings').set_brightness(self.brightness.value())
  except Exception as e:QMessageBox.warning(self,'GITM',str(e))
 def icon(self,name):
  p=ROOT/'assets/desktop'/f'{name}.svg'
  if not p.exists():p=ROOT/'assets/tools'/f'{name}.svg'
  if not p.exists():p=ROOT/'assets/tools'/'settings.svg'
  return QIcon(str(p))
 def resizeEvent(self,event):
  super().resizeEvent(event)
  if not hasattr(self,'app_grid'):return
  columns=5 if self.width()>=1250 else 3 if self.width()>=850 else 2
  for i,(_,b) in enumerate(self.tiles):self.app_grid.addWidget(b,i//columns,i%columns)
  self.update_background()
 def update_background(self):
  if self.wallpaper.isNull():return
  scaled=self.wallpaper.scaled(self.size(),Qt.KeepAspectRatioByExpanding,Qt.SmoothTransformation)
  self.background=scaled.copy((scaled.width()-self.width())//2,(scaled.height()-self.height())//2,self.width(),self.height())
  tiny=self.background.scaled(max(1,self.width()//30),max(1,self.height()//30),Qt.IgnoreAspectRatio,Qt.SmoothTransformation)
  self.blurred=tiny.scaled(self.size(),Qt.IgnoreAspectRatio,Qt.SmoothTransformation)
  for panel in self.findChildren(GlassPanel):panel.update()
 def paintEvent(self,event):
  p=QPainter(self)
  if not self.background.isNull():p.drawPixmap(0,0,self.background)
  else:p.fillRect(self.rect(),QColor('#081a30'))
  p.fillRect(self.rect(),QColor(3,10,22,40))
 def filter_apps(self,text):
  for label,button in self.tiles: button.setVisible(text.casefold() in label.casefold())
 def refresh(self):
  self.clock.setText(datetime.datetime.now().strftime('%a %d %b  %H:%M'))
  if hasattr(self,'radios'):self.refresh_radios()
  try:
   from system_settings import metrics
   m=metrics();g=1024**3
   self.stats.setText(f"المساحة المتاحة  {m['disk_free']/g:.1f} GB · RAM {m['ram_total']/g:.1f} GB")
   for key,used,total in [('ram',m['ram_total']-m['ram_available'],m['ram_total']),('disk',m['disk_total']-m['disk_free'],m['disk_total'])]:
    percent=round(100*used/total);bar,value=self.stat_rows[key];bar.setValue(percent);value.setText(str(percent)+'%')
  except Exception: self.stats.setText('تعذرت قراءة حالة النظام')
 def launch(self,key,argv):
  running=self.processes.get(key)
  if running and running.state()!=QProcess.NotRunning:
   if key=='autodiag' and shutil.which('wmctrl'):QProcess.startDetached('wmctrl',['-a','GITM AutoDiag'])
   if 'update' in argv: QMessageBox.information(self,'GITM','اختر تحديثات البرنامج داخل نافذة AutoDiag المفتوحة.')
   return
  if not Path(argv[0]).is_file() and not shutil.which(argv[0]):
   QMessageBox.information(self,'GITM','هذا البرنامج غير مثبت: '+argv[0]);return
  p=QProcess(self);p.setProgram(argv[0]);p.setArguments(argv[1:]);p.setWorkingDirectory(str(ROOT))
  STATE.mkdir(parents=True,exist_ok=True);p.setStandardErrorFile(str(STATE/(key+'.log')),QIODevice.Append)
  p.errorOccurred.connect(lambda error:QMessageBox.warning(self,'GITM','تعذر تشغيل '+key))
  p.finished.connect(lambda code,status:QMessageBox.warning(self,'GITM',f'توقف {key} برمز {code}. سجل التفاصيل: {STATE/(key+".log")}') if code else None)
  self.processes[key]=p;p.start()
 def activate(self,key):
  if key=='autodiag':self.launch(key,[sys.executable,str(ROOT/'start_release.py'),'--windowed','--skip-intro'])
  elif key=='settings':self.settings()
  elif key=='updates':self.updates()
  else:
   item=next(x for x in APPS if x[0]==key);self.launch(key,item[4])
 def panel(self,title):
  d=QDialog(self);d.setWindowTitle(title);d.setMinimumWidth(560);d.setStyleSheet(STYLE);v=QVBoxLayout(d);v.setContentsMargins(24,24,24,24);v.setSpacing(14)
  h=QLabel(title);h.setStyleSheet('font-size:27px;font-weight:bold');v.addWidget(h)
  self.dialogs.append(d);d.finished.connect(lambda _:self.dialogs.remove(d));return d,v
 def action(self,v,title,key,command):
  b=QPushButton(title);b.setEnabled(bool(shutil.which(command[0])));b.setToolTip(' '.join(command));b.clicked.connect(lambda:self.launch(key,command));v.addWidget(b);return b
 def settings(self):
  d,v=self.panel('مركز التحكم والإعدادات')
  for title,key,cmd in [('Wi-Fi والشبكات','network',['nm-connection-editor']),('Bluetooth','bluetooth',['blueman-manager']),('الصوت','sound',['pavucontrol']),('الشاشة والسطوع والطاقة','power-settings',['systemsettings5']),('دقة الشاشة','display',['systemsettings5']),('لوحة المفاتيح على الشاشة','keyboard',['onboard']),('مراقبة العمليات','tasks',['plasma-systemmonitor'])]:self.action(v,title,key,cmd)
  self.action(v,'الحسابات وكلمة المرور','password',['systemsettings5','kcm_users'])
  d.show()
 def updates(self):
  d,v=self.panel('مركز التحديثات')
  label=QLabel('تحديث حزم النظام عبر Ubuntu، وتحديث AutoDiag عبر حزمة موقّعة.\nفي جلسة Live دون تخزين دائم، تضيع التغييرات بعد إعادة التشغيل.');label.setWordWrap(True);v.addWidget(label)
  self.action(v,'فحص تحديثات النظام','system-update',['plasma-discover'])
  b=QPushButton('فتح تحديثات AutoDiag الموقعة');b.clicked.connect(lambda:self.launch('autodiag',[sys.executable,str(ROOT/'start_release.py'),'--windowed','--skip-intro','--tool','update']));v.addWidget(b)
  d.show()
 def power(self):
  d,v=self.panel('خيارات الطاقة')
  for label,action in [('تعليق الجهاز','suspend'),('إعادة التشغيل','reboot'),('إيقاف التشغيل','poweroff')]:
   b=QPushButton(label);b.clicked.connect(lambda checked=False,a=action:self.confirm_power(a));v.addWidget(b)
  d.show()
 def confirm_power(self,action):
  if QMessageBox.question(self,'GITM','تنفيذ '+action+'؟ احفظ عملك أولًا.')==QMessageBox.Yes:self.launch('power',['systemctl',action])
 def closeEvent(self,event):
  if any(p.state()!=QProcess.NotRunning for p in self.processes.values()):
   QMessageBox.information(self,'GITM','أغلق التطبيقات المفتوحة قبل إنهاء الجلسة.');event.ignore()
  else:event.accept()

def main():
 app=QApplication(sys.argv);app.setApplicationName('GITM OS');app.setLayoutDirection(Qt.RightToLeft)
 w=Desktop()
 if '--smoke' in sys.argv:
  w.show()
  def capture():
   dest=os.environ.get('GITM_SCREENSHOT','gitm-desktop.png')
   app.exit(0 if w.grab().save(dest) else 2)
  QTimer.singleShot(500,capture)
 else:
  w.showFullScreen()
  def visible_marker():
   if w.isVisible():
    __import__('subprocess').run(['logger','-t','gitm','GITM_DESKTOP_VISIBLE'],check=False)
  QTimer.singleShot(4000,visible_marker)
 return app.exec()
if __name__=='__main__':sys.exit(main())
