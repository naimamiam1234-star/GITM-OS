"""Native workshop shell: shared navigation and measured context, no vehicle I/O."""
import re,time,types
from pathlib import Path
from shiboken6 import isValid
from PySide6.QtCore import Qt,QTimer,QSize,QEvent,QObject
from PySide6.QtGui import QShortcut,QKeySequence,QAction,QPalette,QColor
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QLabel,QPushButton,QLineEdit,QComboBox,QMenu,QStackedWidget,QSizePolicy,QScrollArea,QTabWidget
import transport,store
from i18n import language,change_language
from professional_components import triple as t,InfoCard,action_button,icon,styles,palette,header_icon

# Keys retain the existing20 home launchers/gallery mapping without unsupported claims.
ENTRIES=[('diagnosis',('فحص OBD','Diagnostic OBD','OBD scan'),'smart','diagnosis_page',0),('vehicle',('اختيار السيارة','Véhicule','Vehicle'),'car','vehicle_page',0),('service',('وظائف الصيانة','Entretien','Service functions'),'tools','service_page',1),('adapter',('المحولات','Adaptateurs','Adapters'),'engine','adapter_page',2),('tpms',('TPMS','TPMS','TPMS'),'tpms',None,1),('updates',('التحديثات','Mises à jour','Updates'),'update',None,5),('history',('سجل التشخيص','Historique','History'),'history','reports_page',4),('ai',('المساعد الذكي','Assistant IA','AI assistant'),'ai','ai_page',4),('can',('محلل CAN','Analyseur CAN','CAN analyzer'),'can',None,2),('reports',('التقارير','Rapports','Reports'),'reports','reports_page',4),('coverage',('التغطية الفعلية','Couverture','Coverage'),'coverage','engines_page',3),('settings',('الإعدادات','Paramètres','Settings'),'settings','settings_page',5),('dtc',('مرجع الأعطال','Référence DTC','DTC reference'),'dtc','dtc_page',3),('wiring',('ربط VCI','Câblage VCI','VCI wiring'),'vci','wiring_page',3),('live',('البيانات الحية','Données directes','Live data'),'live','diagnosis_page',0),('data',('المراجع المحلية','Références','Local references'),'data','sources_page',3),('scope',('أوسيلوسكوب','Oscilloscope','Oscilloscope'),'live','scope_page',2),('repair',('معلومات الإصلاح','Réparation','Repair information'),'reports','sources_page',3),('oem',('بوابات OEM','Portails OEM','OEM portals'),'coverage','sources_page',3),('ecu',('تعريفات ECU','Profils ECU','ECU profiles'),'engine','engines_page',0)]
GROUPS=[('التشخيص','Diagnostic','Diagnosis'),('الصيانة','Entretien','Service'),('الأدوات','Outils','Tools'),('المعرفة','Connaissances','Knowledge'),('الورشة','Atelier','Workshop'),('النظام','Système','System')]
FACTORIES={'diagnosis':'diagnostic_workspace','live':'diagnostic_workspace','ecu':'ecu_workspace','coverage':'ecu_workspace','adapter':'vci_workspace','vehicle':'vehicle_workspace','reports':'workshop_workspace','history':'workshop_workspace','ai':'ai_workspace','updates':'update_workspace','can':'can_workspace','dtc':'knowledge_workspace'}

class CloseGuard(QObject):
 def __init__(self,w):super().__init__(w);self.w=w;w.installEventFilter(self)
 def eventFilter(self,obj,event):
  if event.type()==QEvent.Close:
   worker=getattr(self.w,'_obd_worker',None)
   if worker is not None and isValid(worker) and worker.isRunning():
    worker.cancel.set();self.w.professional_shell.context.setText(t('جارٍ إنهاء الطلب بأمان','Fin de requête','Finishing current request'));event.ignore();return True
  if event.type()==QEvent.KeyPress and event.key()==Qt.Key_Escape and self.w.isFullScreen():self.w.showMaximized();return True
  return False

class Shell:
 def __init__(self,w):
  self.w=w;self.cache={};self.names={};self.current='home';self.pending=None;self.group=None;self.notifications=[];self.last_report=None;self.dark=False;self.recent_check=0
  import system_settings
  self.theme=system_settings.preferences().get('theme','auto');self.font=system_settings.preferences().get('font_size',16)
  w.menuBar().clear();w.menuBar().hide();w.vehicle=dict(w.vehicle or store.cache('vehicle_selection') or {});old=w.centralWidget();w.takeCentralWidget();old.deleteLater();w.setWindowFlags(Qt.Window);w.setWindowTitle('GITM AutoDiag · Professional Interface');w.setMinimumSize(780,620)
  root=QWidget();w.setCentralWidget(root);outer=QVBoxLayout(root);outer.setContentsMargins(0,0,0,0);outer.setSpacing(0);w.layout=outer
  header=QWidget();header.setObjectName('header');hl=QHBoxLayout(header);hl.setContentsMargins(12,8,12,8)
  toggle=action_button('☰');toggle.setAccessibleName(t('القائمة الجانبية','Navigation','Navigation'));toggle.setMaximumWidth(44);toggle.clicked.connect(lambda:self.sidebar.setVisible(not self.sidebar.isVisible()));hl.addWidget(toggle)
  brand=QLabel('GITM AutoDiag');brand.setObjectName('brand');hl.addWidget(brand);self.title=QLabel(t('الرئيسية','Accueil','Home'));self.title.setObjectName('pageTitle');self.title.setSizePolicy(QSizePolicy.Ignored,QSizePolicy.Preferred);hl.addWidget(self.title,1)
  self.search=QLineEdit();self.search.setPlaceholderText(t('بحث أو P0401','Recherche ou P0401','Search or P0401'));self.search.setMaximumWidth(230);self.search.textChanged.connect(self.filter);self.search.returnPressed.connect(self.search_action);hl.addWidget(self.search)
  self.lang=QComboBox();self.lang.addItems(['العربية','Français','English']);self.lang.setCurrentIndex({'ar':0,'fr':1,'en':2}[language()]);self.lang.currentIndexChanged.connect(self.set_language);hl.addWidget(self.lang)
  self.appearance=action_button('◐');self.appearance.setAccessibleName(t('المظهر','Apparence','Appearance'));am=QMenu(self.appearance)
  for label,key in [(t('نهاري','Clair','Light'),'light'),(t('ليلي','Sombre','Dark'),'dark'),(t('تلقائي','Auto','Auto'),'auto')]:am.addAction(label,lambda key=key:self.set_theme(key))
  self.appearance.setMenu(am);self.appearance.setMaximumWidth(46);hl.addWidget(self.appearance)
  self.split=action_button('▥');self.split.setAccessibleName(t('تقسيم الشاشة','Écran partagé','Split screen'));sm=QMenu(self.split);sm.addAction(t('مقارنة تقريرين','Comparer deux rapports','Compare reports'),lambda:self.navigate('reports'));sm.addAction(t('الأعطال والبيانات الحية','DTC et données','DTC and live data'),self.split_view);unsupported=sm.addAction(t('سيارتان: دعم غير معتمد','Deux véhicules: non validé','Two vehicles: not validated'));unsupported.setEnabled(False);self.split.setMenu(sm);self.split.setMaximumWidth(46);hl.addWidget(self.split)
  self.bell=action_button('●');self.bell.setAccessibleName(t('الإشعارات','Notifications','Notifications'));nm=QMenu(self.bell);nm.aboutToShow.connect(self.alert_menu);self.bell.setMenu(nm);self.bell.setMaximumWidth(42);hl.addWidget(self.bell);outer.addWidget(header)
  for button,kind in ((toggle,'menu'),(self.appearance,'appearance'),(self.split,'split'),(self.bell,'notifications')):button.setText('');button.setIcon(header_icon(kind));button.setIconSize(QSize(24,24))
  middle=QHBoxLayout();middle.setContentsMargins(0,0,0,0);outer.addLayout(middle,1);self.sidebar=QWidget();self.sidebar.setObjectName('sidebar');self.sidebar.setFixedWidth(172);side=QVBoxLayout(self.sidebar);side.setContentsMargins(8,12,8,12);home=action_button(t('الرئيسية','Accueil','Home'),icon='home');home.clicked.connect(self.home);side.addWidget(home)
  for i,group in enumerate(GROUPS):
   b=action_button(t(*group));menu=QMenu(b)
   for key,labels,ico,method,g in ENTRIES:
    if g==i:menu.addAction(icon(ico),t(*labels),lambda key=key:self.navigate(key))
   b.setMenu(menu);side.addWidget(b)
  side.addStretch();full=action_button(t('ملء الشاشة F11','Plein écran F11','Fullscreen F11'));full.clicked.connect(self.fullscreen);side.addWidget(full);middle.addWidget(self.sidebar)
  w.pages=QStackedWidget();middle.addWidget(w.pages,1);w.pages.currentChanged.connect(self.page_changed)
  self.build_home();footer=QWidget();footer.setObjectName('footer');fl=QHBoxLayout(footer);fl.setContentsMargins(14,7,14,7);self.context=QLabel();self.context.setWordWrap(True);fl.addWidget(self.context,1);w.status=self.context;outer.addWidget(footer)
  w.page=self.page;w.go_home=self.home
  callbacks={'diagnosis_page':'diagnosis','vehicle_page':'vehicle','adapter_page':'adapter','reports_page':'reports','ai_page':'ai','engines_page':'ecu','dtc_page':'dtc','service_page':'service','settings_page':'settings'}
  for method,key in callbacks.items():setattr(w,method,lambda key=key:self.navigate(key))
  w.pending_page=lambda title:__import__('support_workspace').show(w,title)
  import workshop_tools
  if not hasattr(workshop_tools,'_system_camera_backend'):workshop_tools._system_camera_backend=workshop_tools.camera
  for key in ('camera','pdf','media','calculator','updates'):
   setattr(workshop_tools,key,lambda window,key=key:__import__('system_services').show(window,key))
  for key in ('customers','invoices','invoice_history'):
   setattr(workshop_tools,key,lambda window,key=key:getattr(__import__('business_workspace'),key)(window))
  w.sources_page=lambda:__import__('resource_workspace').show(w,'sources')
  w.wiring_page=lambda:__import__('resource_workspace').show(w,'wiring')
  w.split_page=self.split_view
  workshop_menu=[b for b in self.sidebar.findChildren(QPushButton) if b.menu()][4].menu()
  for key,labels in [('customers',('العملاء','Clients','Customers')),('invoices',('الفواتير','Factures','Invoices')),('invoice_history',('سجل الفواتير','Historique factures','Invoice history'))]:workshop_menu.addAction(t(*labels),lambda key=key:getattr(workshop_tools,key)(w))
  w.close_guard=CloseGuard(w);w.professional_shell=self
  self.timer=QTimer(w);self.timer.setInterval(1000);self.timer.timeout.connect(self.refresh);self.timer.start()
  QShortcut(QKeySequence('F11'),w,activated=self.fullscreen);QShortcut(QKeySequence('Ctrl+K'),w,activated=self.search.setFocus)
  self.apply_theme();self.refresh();self.page_changed()
 def build_home(self):
  w=self.w;home=QWidget();body=QVBoxLayout(home);body.setContentsMargins(14,10,14,10);body.setSpacing(8);self.vehicle_card=InfoCard(t('السيارة الحالية','Véhicule actuel','Current vehicle'));self.vehicle_label=QLabel();self.vehicle_label.setWordWrap(True);self.vehicle_card.body.addWidget(self.vehicle_label);body.addWidget(self.vehicle_card)
  row=QHBoxLayout();allb=action_button(t('الكل','Tout','All'));allb.clicked.connect(lambda:self.select_group(None));row.addWidget(allb)
  for i,group in enumerate(GROUPS[:5]):
   b=action_button(t(*group));b.clicked.connect(lambda checked=False,i=i:self.select_group(i));row.addWidget(b)
  body.addLayout(row);tiles=QWidget();self.grid=QGridLayout(tiles);self.grid.setContentsMargins(0,0,0,0);self.grid.setSpacing(8);body.addWidget(tiles,1);w.home_cards=[]
  for i,(key,labels,ico,method,group) in enumerate(ENTRIES):
   b=QPushButton();b.setObjectName('card');b.setAccessibleName(t(*labels));b.clicked.connect(lambda checked=False,key=key:self.navigate(key));b.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding);b.setMinimumHeight(62);row=QHBoxLayout(b);row.setContentsMargins(8,5,8,5);image=QLabel();image.setPixmap(icon(ico).pixmap(36,36));image.setFixedSize(36,36);image.setAttribute(Qt.WA_TransparentForMouseEvents);row.addWidget(image);label=QLabel(t(*labels));label.setObjectName('cardlabel');label.setWordWrap(True);label.setAttribute(Qt.WA_TransparentForMouseEvents);row.addWidget(label,1);self.grid.addWidget(b,i//4,i%4);w.home_cards.append(b)
  self.recents=QLabel();self.recents.setObjectName('muted');self.recents.setWordWrap(True);body.addWidget(self.recents);w.pages.addWidget(home);self.names[home]=t('الرئيسية','Accueil','Home');self.cache['home']=home
 def page(self,title):
  w=self.w;w.live=False;w.timer.stop();outer=QWidget();container=QVBoxLayout(outer);container.setContentsMargins(0,0,0,0);scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff);container.addWidget(scroll);p=QWidget();scroll.setWidget(p);l=QVBoxLayout(p);l.setContentsMargins(12,8,12,8);l.setSpacing(8);w.pages.addWidget(outer);self.names[outer]=title;w.pages.setCurrentWidget(outer)
  if self.pending:self.cache[self.pending]=outer
  return l
 def factory(self,module):
  widget=__import__(module).show(self.w)
  if module in ('vehicle_workspace','ecu_workspace'):widget._shell_vehicle_context=dict(self.w.vehicle)
  if module=='diagnostic_workspace':self.w.diagnostic_workspace=widget
  elif module=='ecu_workspace':self.w.ecu_workspace=widget
  elif module=='can_workspace':self.w.can_workspace=widget
  return widget
 def navigate(self,key):
  self.current=key
  if key in self.cache:
   page=self.cache[key];self.w.pages.setCurrentWidget(page)
   for child in page.findChildren(QWidget):
    if hasattr(child,'_shell_vehicle_context') and child._shell_vehicle_context!=self.w.vehicle:
     for name,field in child.fields.items():field.setText(str(self.w.vehicle.get(name,'') or ''))
     child._shell_vehicle_context=dict(self.w.vehicle)
    for method in ('refresh_connection','refresh_state','reload'):
     if hasattr(child,method):getattr(child,method)()
    if child.__class__.__module__=='diagnostic_workspace' and child.__class__.__name__=='Workspace':self.w.diagnostic_workspace=child
   return
  entry=next((e for e in ENTRIES if e[0]==key),None)
  if entry is None:return
  self.pending=key
  try:
   if key=='updates':__import__('system_services').show(self.w,'updates')
   elif key=='settings':__import__('system_services').show(self.w,'settings')
   elif key in FACTORIES:self.factory(FACTORIES[key])
   elif key in ('tpms','service'):__import__('support_workspace').show(self.w,key)
   elif entry[3]:getattr(self.w,entry[3])()
  finally:self.pending=None
 def home(self):
  self.w.live=False;self.w.timer.stop();self.current='home';self.w.pages.setCurrentWidget(self.cache['home']);self.refresh()
 def page_changed(self,*args):
  p=self.w.pages.currentWidget();self.title.setText(self.names.get(p,t('أداة الورشة','Outil atelier','Workshop tool')));self.title.setToolTip(self.title.text())
 def select_group(self,group):self.group=group;self.filter(self.search.text());self.home()
 def filter(self,text):
  matched=[]
  for i,e in enumerate(ENTRIES):
   b=self.w.home_cards[i];visible=(self.group is None or e[4]==self.group) and str(text).casefold() in (' '.join(e[1])+' '+e[0]).casefold();b.setVisible(visible)
   if visible:matched.append(b)
  for i,b in enumerate(matched):self.grid.addWidget(b,i//4,i%4)
 def search_action(self):
  code=self.search.text().strip().upper()
  if re.fullmatch('[PBCU][0-9A-F]{4}',code):
   self.navigate('dtc');widget=self.w.pages.currentWidget().findChild(QLineEdit)
   if widget:widget.setText(code)
  else:self.home()
 def set_theme(self,key):
  import system_settings
  self.theme=key;system_settings.save_preferences({**system_settings.preferences(),'theme':key});self.apply_theme()
 def apply_theme(self):
  self.dark=self.theme=='dark' or self.theme=='auto' and (time.localtime().tm_hour>=19 or time.localtime().tm_hour<7);self.w.setProperty('gitmDark',self.dark);colors=palette(self.dark);pal=self.w.palette()
  for role,key in [(QPalette.Window,'background'),(QPalette.Base,'surface'),(QPalette.Text,'text'),(QPalette.WindowText,'text'),(QPalette.Button,'surface'),(QPalette.ButtonText,'text'),(QPalette.Highlight,'primary'),(QPalette.HighlightedText,'on_primary'),(QPalette.Mid,'muted')]:pal.setColor(role,QColor(colors[key]))
  self.w.setPalette(pal);self.w.setStyleSheet(styles(self.dark,self.font));self.w.base_style=self.w.styleSheet()
 def set_language(self,index):
  if getattr(self.w,'_obd_worker',None) is not None or getattr(self.w,'task',None) is not None and self.w.task.isRunning():
   self.lang.blockSignals(True);self.lang.setCurrentIndex({'ar':0,'fr':1,'en':2}[language()]);self.lang.blockSignals(False);return
  change_language(['ar','fr','en'][index],self.w)
  from professional_components import TRANSLATIONS
  import diagnostic_workspace,ecu_workspace
  for values in list(diagnostic_workspace.WORDS.values())+list(diagnostic_workspace.HEADERS.values())+list(ecu_workspace.WORDS.values()):
   if len(values)==3:
    for value in values:TRANSLATIONS[value]=values
  def translate(text):return TRANSLATIONS.get(text,(text,text,text))[index]
  for obj in self.w.findChildren(QObject):
   for getter,setter in [('text','setText'),('title','setTitle'),('placeholderText','setPlaceholderText'),('accessibleName','setAccessibleName')]:
    if hasattr(obj,getter) and hasattr(obj,setter):
     value=getattr(obj,getter)()
     if isinstance(value,str):getattr(obj,setter)(translate(value))
   if isinstance(obj,QComboBox) and obj is not self.lang:
    for i in range(obj.count()):obj.setItemText(i,translate(obj.itemText(i)))
   if isinstance(obj,QTabWidget):
    for i in range(obj.count()):obj.setTabText(i,translate(obj.tabText(i)))
   if hasattr(obj,'columnCount') and hasattr(obj,'horizontalHeaderItem'):
    for i in range(obj.columnCount()):
     item=obj.horizontalHeaderItem(i)
     if item:item.setText(translate(item.text()))
  for page,title in list(self.names.items()):self.names[page]=translate(title)
  ui=getattr(self.w,'diagnostic_workspace',None)
  if ui and isValid(ui) and ui.report:ui.display(ui.report)
  self.page_changed();self.refresh()

 def fullscreen(self):self.w.showMaximized() if self.w.isFullScreen() else self.w.showFullScreen()
 def split_view(self):
  self.navigate('diagnosis');ui=getattr(self.w,'diagnostic_workspace',None)
  if ui:
   if hasattr(ui,'show_split'):ui.show_split()
   else:ui.tabs.setCurrentIndex(2)
 def alert_menu(self):
  menu=self.bell.menu();menu.clear()
  for text in self.notifications[-6:] or [t('لا توجد إشعارات','Aucune notification','No notifications')]:menu.addAction(text).setEnabled(False)
 def refresh(self):
  info=transport.LINK.info();v=self.w.vehicle;vehicle=' · '.join(str(v.get(k,'')) for k in ('make','model','year','engine') if v.get(k));self.vehicle_label.setText(vehicle or t('اختر سيارة أو اتصل بمحول','Choisir véhicule ou adaptateur','Choose a vehicle or adapter'));ui=getattr(self.w,'diagnostic_workspace',None);voltage='—';report=getattr(ui,'report',None)
  if report and info.get('connected') and ui.connection_key()==ui.connection_identity and report.get('vehicle')==v:
   samples=[r for r in ui.samples if r.get('pid')==0x42 and isinstance(r.get('value'),(int,float))]
   if samples:voltage=str(samples[-1]['value'])+' V · '+str(samples[-1].get('at',''))
  protocol=info.get('protocol_number');protocol_names={6:'CAN 11/500',7:'CAN 29/500',8:'CAN 11/250',9:'CAN 29/250'}
  self.context.setText(('● '+t('متصل','Connecté','Connected') if info.get('connected') else '○ '+t('غير متصل','Déconnecté','Disconnected'))+' · '+str(info.get('adapter') or '—')+' · '+str(info.get('target') or '—')+' · '+protocol_names.get(protocol,'—')+' · '+t('الجهد','Tension','Voltage')+': '+voltage+(' · '+vehicle if vehicle else ''))
  if report and report.get('id')!=self.last_report:self.last_report=report.get('id');self.notifications.append(t('حُفظ فحص؛ راجع الحالة والأخطاء','Scan enregistré; vérifier erreurs','Scan saved; review status and errors'))
  if time.monotonic()-self.recent_check>10:
   self.recent_check=time.monotonic()
   try:
    import json
    with store.db() as db:rows=db.execute('SELECT vehicle,command FROM reports ORDER BY id DESC LIMIT 3').fetchall()
    self.recents.setText(t('آخر العمليات: ','Opérations récentes: ','Recent operations: ')+' | '.join(str(json.loads(v).get('make','—'))+' '+str(json.loads(v).get('model',''))+' · '+cmd for v,cmd in rows))
   except Exception:self.recents.setText(t('تعذر قراءة السجل','Historique indisponible','History unavailable'))

def install(window):
 if hasattr(window,'professional_shell'):return
 Shell(window)
