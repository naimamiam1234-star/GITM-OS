"""GITM desktop session. Native Linux launchers; no simulated vehicle data."""
import os
import sys
import shutil
import datetime
import json
import re
from pathlib import Path
from PySide6.QtCore import Qt, QSize, QTimer, QProcess, QIODevice, QRectF, QRect, QPoint, QPropertyAnimation, QEasingCurve, QSequentialAnimationGroup
from PySide6.QtGui import QIcon, QFontDatabase, QPainter, QColor, QLinearGradient, QPainterPath, QPixmap, QPen
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
 QGridLayout, QLabel, QPushButton, QLineEdit, QFrame, QDialog, QMessageBox, QScrollArea, QSlider, QProgressBar, QFileDialog, QLayout, QSizePolicy, QComboBox, QCheckBox)

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
QLabel#title{font-size:34px;font-weight:bold;} QLabel#muted{color:#b6c5de;font-size:16px;}
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
QComboBox{background:#102238;color:#f0f5ff;border:1px solid #425572;border-radius:10px;padding:8px;}
QComboBox QAbstractItemView{background:#102238;color:#f0f5ff;selection-background-color:#12518c;}
QCheckBox{spacing:10px;}QCheckBox::indicator{width:20px;height:20px;border:1px solid #425572;border-radius:5px;background:#102238;}
QCheckBox::indicator:checked{background:#278aff;border-color:#278aff;}
'''
STYLE+='QCheckBox::indicator:checked{image:url('+str(ROOT/'assets/desktop/check.svg')+');}'


class GlassPanel(QFrame):
 def __init__(self,desktop,parent=None):
  super().__init__(parent);self.desktop=desktop
 def paintEvent(self,event):
  p=QPainter(self);p.setRenderHint(QPainter.Antialiasing)
  bounds=QRectF(self.rect()).adjusted(.5,.5,-.5,-.5)
  clip=QPainterPath();clip.addRoundedRect(bounds,22,22);p.setClipPath(clip)
  light=self.desktop.appearance.get('mode')=='light'
  if not self.desktop.appearance.get('performance') and not light and not self.desktop.blurred.isNull():
   pos=self.mapTo(self.desktop,QPoint(0,0));p.drawPixmap(self.rect(),self.desktop.blurred,QRect(pos,self.size()))
  gradient=QLinearGradient(0,0,self.width(),self.height());gradient.setColorAt(0,QColor('#f4f7fc' if light else '#101d2f'));gradient.setColorAt(1,QColor('#e8eef7' if light else '#08111c'));p.fillRect(self.rect(),gradient)
  p.setClipping(False);p.setPen(QPen(QColor(158,188,219,65),1));p.drawRoundedRect(bounds,22,22)


class UsageRing(QWidget):
 def __init__(self,title,parent=None):
  super().__init__(parent);self.title=title;self.value=None;self.setMinimumSize(80,80)
 def setValue(self,value):
  self.value=max(0,min(100,value));self.update()
 def paintEvent(self,event):
  p=QPainter(self);p.setRenderHint(QPainter.Antialiasing)
  side=min(self.width(),self.height())-18;r=QRectF((self.width()-side)/2,(self.height()-side)/2,side,side)
  light=getattr(self.window(),'appearance',{}).get('mode')=='light'
  p.setPen(QPen(QColor('#c4d3e5' if light else '#29425f'),7));p.drawEllipse(r)
  if self.value is not None:
   p.setPen(QPen(QColor('#339cff'),7,Qt.SolidLine,Qt.RoundCap));p.drawArc(r,90*16,-round(self.value*3.6*16))
  p.setPen(QColor('#172b45' if light else '#f0f5ff'));p.drawText(r.adjusted(0,10,0,-20),Qt.AlignCenter,self.title)
  p.setPen(QColor('#1853a3' if light else '#91caff'));p.drawText(r.adjusted(0,35,0,0),Qt.AlignCenter,'—' if self.value is None else str(self.value)+'%')

class Desktop(QWidget):
 def __init__(self):
  super().__init__()
  self.setWindowTitle('GITM OS 3.3 · Desktop')
  self.setWindowFlags(Qt.Window|Qt.FramelessWindowHint|Qt.WindowStaysOnBottomHint)
  self.resize(1440,900);self.processes={};self.dialogs=[];self.tiles=[];self.app_buttons={};self.control_radios={};self.sync_phase=0
  self.appearance={'mode':'dark','performance':False,'reduce_motion':False,'icon_size':64}
  try:
   saved=json.loads((STATE/'appearance.json').read_text())
   if saved.get('mode') in ('dark','light'):self.appearance['mode']=saved['mode']
   for key in ('performance','reduce_motion'):self.appearance[key]=saved.get(key) is True
   size=saved.get('icon_size',64)
   if type(size) is int and 48<=size<=68:self.appearance['icon_size']=size
  except (OSError,ValueError,AttributeError):pass
  self.wallpaper=QPixmap(str(ROOT/'assets/desktop/wallpaper.png'));self.background=QPixmap();self.blurred=QPixmap()
  try:
   personal=QPixmap((STATE/'wallpaper-path.txt').read_text().strip())
   if not personal.isNull():self.wallpaper=personal
  except OSError:pass
  for f in (ROOT/'assets').glob('Tajawal-*.ttf'):QFontDatabase.addApplicationFont(str(f))
  self.setWindowIcon(self.icon('settings'))
  QApplication.setDesktopFileName('gitm-desktop')
  self.setLayoutDirection(Qt.LeftToRight);self.setStyleSheet(STYLE)
  outer=QVBoxLayout(self);outer.setSizeConstraint(QLayout.SetNoConstraint);outer.setContentsMargins(28,18,28,16);outer.setSpacing(14)
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
  power=QPushButton();self.power_button=power;power.setIcon(self.icon('power'));power.setIconSize(QSize(24,24));power.setToolTip('الطاقة');power.setObjectName('nav');power.clicked.connect(self.power);top.addWidget(power);outer.addLayout(top)
  content=QHBoxLayout();content.setSpacing(28)
  left=QVBoxLayout();left.setSpacing(12);content.addLayout(left,1)
  welcome=QHBoxLayout();words=QVBoxLayout();heading=QLabel('مرحبًا بك.');heading.setObjectName('title');words.addWidget(heading)
  subtitle=QLabel('كل أدواتك، في مساحة عمل واحدة.');subtitle.setObjectName('muted');words.addWidget(subtitle);welcome.addLayout(words,1)
  title=QLabel('GITM <span style="color:#248dff">OS</span><br><span style="font-size:12px;letter-spacing:3px;color:#becce1">YOUR WORKSPACE. YOUR WAY.</span>');title.setStyleSheet('font-size:32px;font-family:DejaVu Sans;font-weight:bold');title.setAlignment(Qt.AlignRight|Qt.AlignVCenter);welcome.addWidget(title);left.addLayout(welcome)
  self.search=QLineEdit();self.search.setPlaceholderText('ابحث عن تطبيق، إعدادات أو أدوات…');self.search.textChanged.connect(self.filter_apps);self.search.setLayoutDirection(Qt.RightToLeft);left.addWidget(self.search)
  container=QWidget();grid=QGridLayout(container);grid.setContentsMargins(0,0,0,0);grid.setSpacing(10);self.app_grid=grid;self.app_container=container
  order=['autodiag','documents','photos','media','settings','files','browser','updates','calculator','install']
  for i,key in enumerate(order):
   _,name,desc,icon,command=next(a for a in APPS if a[0]==key)
   card=QWidget();v=QVBoxLayout(card);v.setContentsMargins(2,8,2,8);v.setSpacing(7);v.setAlignment(Qt.AlignCenter)
   b=QPushButton();b.setObjectName('appIcon');b.setIcon(self.icon(icon));b.setIconSize(QSize(64,64));b.setFixedSize(72,72);b.setToolTip(name);b.setAccessibleName(name);self.app_buttons[key]=b;b.clicked.connect(lambda checked=False,k=key:self.activate(k));v.addWidget(b,0,Qt.AlignHCenter)
   label=QLabel(name);label.setAlignment(Qt.AlignCenter);label.setWordWrap(True);label.setStyleSheet('font-weight:bold;font-size:16px');v.addWidget(label)
   grid.addWidget(card,i//5,i%5);self.tiles.append((name+' '+desc+' '+key,card))
  left.addWidget(container,1)
  self.control=GlassPanel(self,self);self.control.setFixedWidth(340);right=QVBoxLayout(self.control);right.setContentsMargins(20,20,20,20);right.setSpacing(15)
  control_title=QLabel('مركز التحكم');control_title.setStyleSheet('font-size:17px;font-weight:bold;color:#a9bbd2');right.addWidget(control_title)
  radios=QGridLayout();right.addLayout(radios)
  for i,(title,icon,fn) in enumerate([('Wi-Fi','wifi',lambda:self.radios.show('wifi')),('Bluetooth','bluetooth',lambda:self.radios.show('bluetooth')),('المظهر','settings',self.choose_appearance),('وضع الطيران','airplane',self.toggle_airplane)]):
   v=QVBoxLayout();b=QPushButton();b.setIcon(self.icon(icon));b.setIconSize(QSize(40,40));b.setFixedSize(60,60);b.setObjectName('radio');self.control_radios[icon]=b;b.clicked.connect(fn);b.setAccessibleName(title);v.addWidget(b,0,Qt.AlignCenter)
   label=QLabel(title);label.setAlignment(Qt.AlignCenter);label.setStyleSheet('font-size:13px');v.addWidget(label);radios.addLayout(v,0,i)
  right.addWidget(self.divider())
  light=QHBoxLayout();light.addWidget(QLabel('☀'));self.brightness=QSlider(Qt.Horizontal);self.brightness.setRange(5,100);self.brightness.setValue(70)
  import system_settings
  self.brightness.setEnabled(bool(system_settings.brightness_devices()));self.brightness.setToolTip('السطوع' if self.brightness.isEnabled() else 'العتاد لا يوفر تحكمًا بالسطوع');self.brightness.sliderReleased.connect(self.apply_brightness);light.addWidget(self.brightness);light.addWidget(QLabel('☀'));right.addLayout(light)
  tools=QGridLayout();right.addLayout(tools)
  for i,(label,icon,key,cmd) in enumerate([('الشاشة','display','display',['systemsettings','kcm_kscreen']),('الصوت','volume','sound',['systemsettings','kcm_pulseaudio']),('لوحة المفاتيح','keyboard','keyboard',['onboard']),('الطاقة','battery','power-settings',['systemsettings','kcm_powerdevilprofilesconfig'])]):
   b=QPushButton(label);b.setIcon(self.icon(icon));b.setIconSize(QSize(24,24));b.setMinimumHeight(60);b.setStyleSheet('padding:8px;font-size:13px;background:rgba(25,38,56,155);border:1px solid #344054;border-radius:12px');b.clicked.connect(lambda checked=False,k=key,c=cmd:self.launch(k,c));tools.addWidget(b,i//2,i%2)
  right.addWidget(self.divider())
  self.settings_button=QPushButton('كل الإعدادات  ›');self.settings_button.clicked.connect(self.settings);right.addWidget(self.settings_button);right.addStretch()
  self.control.hide()
  outer.addLayout(content,1)
  self.system_panel=GlassPanel(self);self.system_panel.setFixedSize(260,260)
  sl=QVBoxLayout(self.system_panel);sl.setContentsMargins(16,16,16,16);sl.setSpacing(12)
  caption=QLabel('حالة النظام');caption.setAlignment(Qt.AlignCenter);sl.addWidget(caption)
  rings=QHBoxLayout();self.stat_rows={}
  for key,title in [('ram','RAM'),('disk','التخزين')]:
   ring=UsageRing(title);rings.addWidget(ring);self.stat_rows[key]=ring
  sl.addLayout(rings,1)
  self.stats=QLabel();self.stats.setStyleSheet('font-size:12px;color:#b5c4d9');self.stats.setWordWrap(True);self.stats.setAlignment(Qt.AlignCenter);sl.addWidget(self.stats)
  content.addWidget(self.system_panel,0,Qt.AlignVCenter)
  dock=GlassPanel(self);dr=QHBoxLayout(dock);dr.setContentsMargins(15,10,15,10);dr.setSpacing(10)
  launcher=QPushButton('⠿');launcher.setObjectName('dockIcon');launcher.setStyleSheet('font-size:29px');launcher.clicked.connect(lambda:self.search.setFocus());dr.addWidget(launcher)
  for key in ['autodiag','files','browser','documents','photos','media','settings']:
   item=next(a for a in APPS if a[0]==key);b=QPushButton();b.setObjectName('dockIcon');b.setIcon(self.icon(item[3]));b.setIconSize(QSize(49,49));b.setFixedSize(56,56);b.setToolTip(item[1]);b.setAccessibleName(item[1]);b.clicked.connect(lambda checked=False,k=key:self.activate(k));dr.addWidget(b)
  outer.addWidget(dock,0,Qt.AlignHCenter)
  if os.environ.get('GITM_NATIVE_PLASMA')=='1':dock.hide()
  from desktop_radios import Radios
  self.radios=Radios(self);self.radios.changed.connect(self.refresh_radios)
  self.refresh_radios()
  self.animation=QTimer(self);self.animation.timeout.connect(self.animate_status);self.animation.start(200)
  self.refresh();self.timer=QTimer(self);self.timer.timeout.connect(self.refresh);self.timer.start(5000)
  self.apply_appearance()
  for button in self.app_buttons.values():button.pressed.connect(lambda b=button:self.animate_icon(b))
 def animate_icon(self,button):
  if self.appearance['reduce_motion'] or self.appearance['performance']:return
  previous=getattr(button,'_gitm_motion',None)
  if previous:previous.stop()
  group=QSequentialAnimationGroup(button)
  size=self.appearance['icon_size']
  for start,end,duration in [(size,size-7,80),(size-7,size,140)]:
   animation=QPropertyAnimation(button,b'iconSize',group);animation.setStartValue(QSize(start,start));animation.setEndValue(QSize(end,end));animation.setDuration(duration);animation.setEasingCurve(QEasingCurve.OutCubic);group.addAnimation(animation)
  button._gitm_motion=group;group.finished.connect(group.deleteLater);group.finished.connect(lambda:setattr(button,'_gitm_motion',None));group.start()
 def theme_css(self,css):
  if self.appearance['mode']!='light':return css
  colors={'#f0f5ff':'#172b45','#b6c5de':'#405978','#bccde7':'#405978','#c9d7eb':'#405978','#b3c4db':'#405978','#a9bbd2':'#405978','#bfcee1':'#405978','#b5c4d9':'#405978','#becce1':'#405978','#77859a':'#56657a','#36485f':'#aebed2','#425572':'#aebed2','#39526f':'#aebed2','#344054':'#aebed2','#455771':'#8497ae','#243246':'#d3dfed','#2c3d51':'#c0cfe0','#102238':'#eef3fa','#132941':'#e3ebf6','#12518c':'#bed9fb'}
  css=re.sub(r'#[0-9a-fA-F]{6}',lambda m:colors.get(m.group().lower(),m.group()),css)
  css=css.replace('color:white','color:#172b45')
  css=re.sub(r'rgba\((22,39,62,195|20,39,61,200|13,26,45,215|25,38,56,155)\)','rgba(238,244,252,245)',css)
  css=css.replace('rgba(42,74,110,225)','rgba(211,227,248,245)')
  return css
 def apply_appearance(self):
  mode=self.appearance['mode']
  if getattr(self,'_native_mode',None)!=mode and shutil.which('plasma-apply-colorscheme'):
   self._native_mode=mode
   QProcess.startDetached('plasma-apply-colorscheme',['BreezeLight' if mode=='light' else 'BreezeDark'])
  self.setStyleSheet(self.theme_css(STYLE))
  for button in self.app_buttons.values():button.setIconSize(QSize(self.appearance['icon_size'],self.appearance['icon_size']))
  for widget in self.findChildren(QWidget):
   if not hasattr(widget,'_gitm_original_style'):widget._gitm_original_style=widget.styleSheet()
   if widget._gitm_original_style:widget.setStyleSheet(self.theme_css(widget._gitm_original_style))
  if self.appearance['performance']:self.blurred=QPixmap()
  self.update_background();self.update()
  for panel in self.findChildren(GlassPanel):panel.update()
  for ring in self.stat_rows.values():ring.update()
  self.refresh_radios()
  for key in ('search','chevron'):self.status_buttons[key].setIcon(self.icon(key))
  self.power_button.setIcon(self.icon('power'))
 def save_appearance(self):
  STATE.mkdir(parents=True,exist_ok=True)
  temp=STATE/'appearance.json.tmp';temp.write_text(json.dumps(self.appearance));temp.replace(STATE/'appearance.json')
  self.apply_appearance()
 def keyPressEvent(self,event):
  if event.key()==Qt.Key_Escape:
   self.control.hide();self.status_buttons['chevron'].setChecked(False);self.search.clear();return
  if event.key()==Qt.Key_F and event.modifiers() & Qt.ControlModifier:self.search.setFocus();return
  super().keyPressEvent(event)
 def toggle_control(self):
  visible=not self.control.isVisible();self.control.setVisible(visible);self.status_buttons['chevron'].setChecked(visible)
  self.position_control();self.control.raise_()
  previous=getattr(self,'control_motion',None)
  if previous:previous.stop()
  if visible and not self.appearance['reduce_motion'] and not self.appearance['performance']:
   end=self.control.pos();self.control.move(end+QPoint(0,-18))
   self.control_motion=QPropertyAnimation(self.control,b'pos',self);self.control_motion.setDuration(180);self.control_motion.setStartValue(self.control.pos());self.control_motion.setEndValue(end);self.control_motion.setEasingCurve(QEasingCurve.OutCubic);self.control_motion.start()
 def position_control(self):
  self.control.setGeometry(max(8,self.width()-self.control.width()-28),68,self.control.width(),min(540,self.height()-86))
 def refresh_radios(self):
  from desktop_radios import battery_info,state_icon
  for key,state in [('wifi',self.radios.wifi_state),('bluetooth',self.radios.bluetooth_state)]:
   icon=state_icon(key,dict(state,light=self.appearance['mode']=='light'));self.status_buttons[key].setIcon(icon)
   if key in self.control_radios:self.control_radios[key].setIcon(icon)
  self.status_buttons['wifi'].setToolTip('Wi-Fi · '+self.radios.wifi)
  self.status_buttons['bluetooth'].setToolTip('Bluetooth · '+self.radios.bluetooth)
  info=battery_info();self.status_buttons['battery'].setIcon(state_icon('battery',dict(info,light=self.appearance['mode']=='light')))
  self.battery_label.setText('' if not info['present'] else str(info['percent'])+'%')
  self.status_buttons['battery'].setToolTip(info['text'])
  self.status_buttons['sync'].setIcon(state_icon('sync',{'busy':self.radios.busy,'phase':self.sync_phase,'light':self.appearance['mode']=='light'}))
 def animate_status(self):
  if self.appearance['reduce_motion']:return
  self.sync_phase=(self.sync_phase+1)%12
  if hasattr(self,'radios') and self.radios.busy:self.status_buttons['sync'].setIcon(__import__('desktop_radios').state_icon('sync',{'busy':True,'phase':self.sync_phase,'light':self.appearance['mode']=='light'}))
 def divider(self):
  line=QFrame();line.setFixedHeight(1);line.setStyleSheet('background:rgba(162,184,211,55)');return line
 def choose_appearance(self):
  self.launch('settings',['systemsettings','kcm_colors'])
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
  icon=QIcon(str(p))
  if name in ('search','chevron','power') and self.appearance['mode']=='light':
   pixmap=icon.pixmap(32,32);painter=QPainter(pixmap);painter.setCompositionMode(QPainter.CompositionMode_SourceIn);painter.fillRect(pixmap.rect(),QColor('#405978'));painter.end();return QIcon(pixmap)
  return icon
 def resizeEvent(self,event):
  super().resizeEvent(event)
  if not hasattr(self,'app_grid'):return
  columns=5
  if hasattr(self,'system_panel'):
   size=260 if self.width()>=1150 else 220;self.system_panel.setFixedSize(size,size)
  if hasattr(self,'control'):self.position_control()
  for i,(_,b) in enumerate(self.tiles):self.app_grid.addWidget(b,i//columns,i%columns)
  self.update_background()
 def update_background(self):
  if self.wallpaper.isNull():return
  scaled=self.wallpaper.scaled(self.size(),Qt.KeepAspectRatioByExpanding,Qt.SmoothTransformation)
  self.background=scaled.copy((scaled.width()-self.width())//2,(scaled.height()-self.height())//2,self.width(),self.height())
  if not self.appearance['performance'] and self.appearance['mode']=='dark':
   tiny=self.background.scaled(max(1,self.width()//30),max(1,self.height()//30),Qt.IgnoreAspectRatio,Qt.SmoothTransformation)
   self.blurred=tiny.scaled(self.size(),Qt.IgnoreAspectRatio,Qt.SmoothTransformation)
  else:self.blurred=QPixmap()
  for panel in self.findChildren(GlassPanel):panel.update()
 def paintEvent(self,event):
  p=QPainter(self)
  if not self.background.isNull():p.drawPixmap(0,0,self.background)
  else:p.fillRect(self.rect(),QColor('#081a30'))
  p.fillRect(self.rect(),QColor(245,248,253,235) if self.appearance['mode']=='light' else QColor(3,10,22,65))
 def filter_apps(self,text):
  for label,button in self.tiles: button.setVisible(text.casefold() in label.casefold())
 def refresh(self):
  self.clock.setText(datetime.datetime.now().strftime('%a %d %b  %H:%M'))
  if hasattr(self,'radios'):self.refresh_radios()
  try:
   from system_settings import metrics
   m=metrics();g=1024**3
   self.stats.setText(f"التخزين المتاح: \u2066{m['disk_free']/g:.1f} GB\u2069\nRAM: \u2066{m['ram_total']/g:.1f} GB\u2069")
   for key,used,total in [('ram',m['ram_total']-m['ram_available'],m['ram_total']),('disk',m['disk_total']-m['disk_free'],m['disk_total'])]:
    percent=round(100*used/total);self.stat_rows[key].setValue(percent)
  except Exception: self.stats.setText('تعذرت قراءة حالة النظام')
 def launch(self,key,argv):
  if argv[0]=='systemsettings':key='settings'
  running=self.processes.get(key)
  if running and running.state()!=QProcess.NotRunning:
   if shutil.which('wmctrl'):
    probe=QProcess(self);probe.setProgram('wmctrl');probe.setArguments(['-lp'])
    def raise_window():
     for line in bytes(probe.readAllStandardOutput()).decode(errors='replace').splitlines():
      fields=line.split(None,4)
      if len(fields)>=3 and fields[2]==str(running.processId()):
       QProcess.startDetached('wmctrl',['-ia',fields[0]]);break
     probe.deleteLater()
    probe.finished.connect(raise_window);probe.start()
   if 'update' in argv: QMessageBox.information(self,'GITM','اختر تحديثات البرنامج داخل نافذة AutoDiag المفتوحة.')
   return
  if not Path(argv[0]).is_file() and not shutil.which(argv[0]):
   QMessageBox.information(self,'GITM','هذا البرنامج غير مثبت: '+argv[0]);return
  p=QProcess(self)
  from PySide6.QtCore import QProcessEnvironment
  env=QProcessEnvironment.systemEnvironment()
  if argv[0]!=sys.executable:
   env.remove('QT_STYLE_OVERRIDE');env.remove('QT_QPA_PLATFORMTHEME')
  env.insert('LANG','ar_MA.UTF-8') if argv[0]=='systemsettings' else None
  p.setProcessEnvironment(env);p.setProgram(argv[0]);p.setArguments(argv[1:]);p.setWorkingDirectory(str(ROOT))
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
  d=QDialog(self);d.setWindowIcon(self.icon('settings'));d.setWindowTitle(title);d.setMinimumWidth(560);d.setStyleSheet(STYLE);v=QVBoxLayout(d);v.setContentsMargins(24,24,24,24);v.setSpacing(14)
  h=QLabel(title);h.setStyleSheet('font-size:27px;font-weight:bold');v.addWidget(h)
  d._gitm_original_style=STYLE;d.setStyleSheet(self.theme_css(STYLE));self.dialogs.append(d);d.finished.connect(lambda _:self.dialogs.remove(d));return d,v
 def action(self,v,title,key,command):
  b=QPushButton(title);b.setEnabled(bool(shutil.which(command[0])));b.setToolTip(' '.join(command));b.clicked.connect(lambda:self.launch(key,command));v.addWidget(b);return b
 def settings(self):
  self.control.hide();self.status_buttons['chevron'].setChecked(False)
  self.launch('settings',['systemsettings'])
 def system_information(self):
  d,v=self.panel('حول GITM OS');d.setLayoutDirection(Qt.RightToLeft)
  from desktop_radios import battery_info
  details=['GITM OS · Ubuntu Linux · x86_64']
  try:
   release=dict(line.split('=',1) for line in Path('/etc/os-release').read_text().splitlines() if '=' in line)
   details.append(release.get('PRETTY_NAME','Linux').strip('"'))
  except OSError:pass
  details.append('النواة: '+os.uname().release)
  try:
   m=__import__('system_settings').metrics();g=1024**3
   details.extend([f"RAM: {m['ram_total']/g:.1f} GB · متاحة {m['ram_available']/g:.1f} GB",f"التخزين: {m['disk_total']/g:.1f} GB · متاح {m['disk_free']/g:.1f} GB"])
  except Exception:details.append('تعذرت قراءة الذاكرة أو التخزين')
  details.extend(['Wi-Fi: '+self.radios.wifi,'Bluetooth: '+self.radios.bluetooth,'البطارية: '+battery_info()['text']])
  label=QLabel('\n\n'.join(details));label.setWordWrap(True);label.setTextInteractionFlags(Qt.TextSelectableByMouse);v.addWidget(label)
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
  if os.environ.get('GITM_NATIVE_PLASMA')=='1':
   screen=app.primaryScreen();w.setGeometry(screen.availableGeometry());w.show()
   screen.availableGeometryChanged.connect(w.setGeometry)
  else:w.showFullScreen()
  if 'gitm.gallery=1' in Path('/proc/cmdline').read_text():
   import gallery_runner
   QTimer.singleShot(6000,lambda:gallery_runner.start(w))
  def visible_marker():
   if w.isVisible():
    __import__('subprocess').run(['logger','-t','gitm','GITM_DESKTOP_VISIBLE'],check=False)
    if os.environ.get('GITM_NATIVE_PLASMA')=='1':
     sp=__import__('subprocess');version=sp.run(['plasmashell','--version'],capture_output=True,text=True).stdout.strip()
     if version.startswith('plasmashell 6.') and sp.run(['pgrep','-x','kwin_x11'],capture_output=True).returncode==0:
      sp.run(['logger','-t','gitm','GITM_PLASMA_SESSION|'+version],check=False)
  QTimer.singleShot(4000,visible_marker)
 return app.exec()
if __name__=='__main__':sys.exit(main())

