"""AutoDiag's application design system. No desktop or ISO behavior here."""
from pathlib import Path
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QFontDatabase, QPixmap, QPainter
from PySide6.QtWidgets import (QWidget,QLabel,QPushButton,QHBoxLayout,QVBoxLayout,
    QGridLayout,QStackedWidget,QComboBox,QScrollArea,QSizePolicy)
from i18n import tr,language,change_language
ROOT=Path(__file__).parent
WORDS={
 'live_title':('البيانات الحية','Données en direct','Live data'),
 'wiring_title':('توصيل المحول','Branchement VCI','VCI wiring'),
 'workspace':('مساحة التشخيص','Espace diagnostic','Diagnostic workspace'),
 'intro':('اختر السيارة، اتصل بالمحول، ثم ابدأ الفحص.','Choisissez le véhicule, connectez le VCI, puis lancez le diagnostic.','Choose a vehicle, connect your VCI, then start a diagnostic session.'),
 'home':('الرئيسية','Accueil','Home'),
 'vehicle':('اختيار السيارة','Véhicule','Vehicle'),
 'diagnosis':('التشخيص','Diagnostic','Diagnostics'),
 'assistant':('المساعد','Assistant','Assistant'),
 'settings':('الإعدادات','Réglages','Settings'),
 'tools':('العملاء','Clients','Customers'),
 'invoice':('الفواتير','Factures','Invoices'),
 'connect':('الاتصال بالمحول','Connexion VCI','Connect VCI'),
 'offline':('المحول غير متصل','VCI déconnecté','VCI disconnected'),
 'hint':('تُحدَّد الوظائف حسب السيارة والمحول والتعريفات المتاحة.','Les fonctions dépendent du véhicule, du VCI et des définitions disponibles.','Functions depend on the vehicle, adapter and available definitions.'),
 'data':('البيانات والمراجع','Données et références','Data & references'),
 'scan':('قراءة الأعطال والبيانات المسجلة','Codes défaut et données enregistrées','Fault codes and recorded data'),
 'select':('تحديد المركبة قبل بدء العمل','Identifier le véhicule avant de commencer','Identify the vehicle before starting'),
 'adapter':('إعداد الاتصال والتحقق من الحالة','Configurer la connexion et vérifier son état','Configure the connection and check its state'),
 'ai':('شرح النتائج والبحث في المصادر','Explications et recherche de sources','Explain findings and research sources'),
 'records':('تقارير الفحص وسجل الإصلاح','Rapports et historique des interventions','Diagnostic reports and repair history'),
 'coverage':('التعريفات وحدود التغطية','Définitions et limites de couverture','Definitions and coverage limits'),
 'maintenance':('إجراءات تتطلب تعريفًا متوافقًا','Procédures nécessitant une définition compatible','Procedures require compatible definitions'),
 'references':('مصادر البيانات ووثائق الإصلاح','Sources et documentation technique','Data sources and repair documentation'),
 'scope':('عرض ملفات القياس المسجلة','Consulter les mesures enregistrées','Review recorded measurement files'),
 'dtc':('البحث عن تعريف رمز العطل','Rechercher la définition d’un code','Look up a fault-code definition'),
}
def word(key):return WORDS[key][{'ar':0,'fr':1,'en':2}[language()]]
# Original, consistently weighted vector icons; no bitmap scaling or mixed packs.
PATHS={
 'car':'<path d="m5 10 2-5h10l2 5M4 10h16v8H4zM7 18v2m10-2v2M7 13h2m6 0h2"/>',
 'smart':'<path d="M4 13V9l2-4h10l2 4M4 9h14M6 13h2m-4 0v5h5"/><circle cx="16" cy="16" r="4"/><path d="m19 19 3 3"/>',
 'vci':'<rect x="3" y="7" width="18" height="11" rx="3"/><path d="M7 11v3m5-3v3m5-3v3M8 4h8"/>',
 'ai':'<path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5ZM19 3v4m-2-2h4"/>',
 'history':'<path d="M13 3H5v18h14V9l-6-6v6h6M8 13h8m-8 4h5"/>',
 'tools':'<path d="M14 4a5 5 0 0 0-6 6L3 17l4 4 7-7a5 5 0 0 0 6-6l-4 3-3-3 3-4Z"/>',
 'dtc':'<path d="m12 3 10 18H2ZM12 9v5m0 3v.2"/>',
 'coverage':'<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c-5 5-5 13 0 18 5-5 5-13 0-18"/>',
 'reports':'<path d="M4 4h6l2 2 2-2h6v16h-6l-2 2-2-2H4ZM12 6v16M6 8h3m-3 4h3m6-4h3m-3 4h3"/>',
 'live':'<path d="M2 12h4l3-8 5 16 3-8h5"/>',
}
def icon(key):
    from PySide6.QtSvg import QSvgRenderer
    svg=('<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 40 40">'
         '<rect width="40" height="40" rx="10" fill="#e8f3ff"/>'
         '<g transform="translate(8 8)" fill="none" stroke="#1769aa" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">'
         +PATHS.get(key,PATHS['reports'])+'</g></svg>')
    pixmap=QPixmap(80,80);pixmap.fill(Qt.transparent);
    painter=QPainter(pixmap);QSvgRenderer(svg.encode()).render(painter);painter.end()
    return QIcon(pixmap)


def setup(w):
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QFrame,QButtonGroup,QApplication
    from workshop_tools import t
    import workshop_tools as wt,transport,store
    from autodiag_experience import install
    install(w)
    QApplication.instance().setLayoutDirection(Qt.RightToLeft if language()=="ar" else Qt.LeftToRight)
    for f in (ROOT/'assets').glob('Tajawal-*.ttf'):QFontDatabase.addApplicationFont(str(f))
    w.design_scale=1
    texts=[]
    def label(text,name='',wrap=True):
        q=QLabel(text);q.setObjectName(name);q.setWordWrap(wrap);return q
    def translated(key,name=''):
        q=label(word(key),name);texts.append((q,key));return q
    def frame(name):q=QFrame();q.setObjectName(name);return q
    header=frame('header');h=QHBoxLayout(header);h.setContentsMargins(24,15,24,15)
    brand=label('GITM  /  AUTODIAG','brand',False);brand.setLayoutDirection(Qt.LeftToRight);h.addWidget(brand)
    h.addStretch();w.session_label=label('','session',False);h.addWidget(w.session_label)
    w.language_picker=QComboBox();w.language_picker.addItems(['العربية','Français','English']);w.language_picker.setCurrentIndex({'ar':0,'fr':1,'en':2}[language()]);w.language_picker.setFixedWidth(135);h.addWidget(w.language_picker)
    w.layout.addWidget(header)
    workspace=QWidget();horizontal=QHBoxLayout(workspace);horizontal.setContentsMargins(0,0,0,0);horizontal.setSpacing(0)
    side=frame('sidebar');side.setMinimumWidth(184);sl=QVBoxLayout(side);sl.setContentsMargins(14,24,14,20);sl.setSpacing(7)
    sl.addWidget(label('AUTODIAG WORKSPACE','sideCaption'))
    group=QButtonGroup(w);group.setExclusive(True);w.navigation_buttons=[]
    entries=[('home','smart',w.go_home),('vehicle','car',w.vehicle_page),('diagnosis','vci',w.diagnosis_page),('assistant','ai',w.ai_page),('tools','history',lambda:wt.customers(w)),('invoice','reports',lambda:wt.invoices(w))]
    for key,art,callback in entries:
        b=QPushButton(word(key));b.setObjectName('navButton');b.setIcon(icon(art));b.setIconSize(QSize(25,25));b.setCheckable(True);group.addButton(b);sl.addWidget(b);texts.append((b,key));w.navigation_buttons.append(b)
        def open_page(checked=False,fn=callback,button=b):fn();button.setChecked(True)
        b.clicked.connect(open_page)
    w.navigation_buttons[0].setChecked(True)
    sl.addSpacing(20);sl.addWidget(label(t('أدوات الفحص','Outils diagnostic','Diagnostic tools'),'sideCaption'))
    for text,art,fn in [(t('مرجع الأعطال','Codes défaut','Fault reference'),'dtc',w.dtc_page),(t('الصيانة','Entretien','Maintenance'),'tools',w.service_page),(t('كاميرا الفحص','Caméra','Inspection camera'),'vci',lambda:wt.camera(w)),(t('المراجع','Références','References'),'reports',w.sources_page)]:
        b=QPushButton(text);b.setObjectName('sideTool');b.setIcon(icon(art));b.setIconSize(QSize(23,23));b.clicked.connect(fn);sl.addWidget(b)
    sl.addStretch();sl.addWidget(label('GITM EXPERIENCE\nAPPLICATION PREVIEW','sideCaption'))
    side_scroll=QScrollArea();side_scroll.setObjectName("sideScroll");side_scroll.setWidgetResizable(True);side_scroll.setFixedWidth(202);side_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff);side_scroll.setFrameShape(QScrollArea.NoFrame);side_scroll.setWidget(side)
    horizontal.addWidget(side_scroll)
    class PageStack(QStackedWidget):
        def minimumSizeHint(self):
            q=self.currentWidget();return q.minimumSizeHint() if q else QSize(0,0)
    w.pages=PageStack();w.pages.currentChanged.connect(w.pages.updateGeometry);horizontal.addWidget(w.pages,1);w.layout.addWidget(workspace,1)
    scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setFrameShape(QScrollArea.NoFrame)
    home=QWidget();body=QVBoxLayout(home);body.setContentsMargins(28,28,28,28);body.setSpacing(20)
    body.addWidget(translated('workspace','welcome'));body.addWidget(translated('intro','subtle'))
    hero=frame('hero');hl=QVBoxLayout(hero);hl.setContentsMargins(24,22,24,22);hl.setSpacing(12)
    hl.addWidget(label(t('جلسة الفحص الحالية','Session diagnostic','Current diagnostic session'),'heroCaption'))
    w.vehicle_summary=label('','heroTitle');hl.addWidget(w.vehicle_summary)
    hl.addWidget(label(t('ابدأ بهوية المركبة واتصال VCI؛ النتائج مرتبطة بجلستك.','Identifiez le véhicule et connectez le VCI.','Identify the vehicle and connect VCI; results belong to your session.'),'heroText'))
    row=QHBoxLayout();hl.addLayout(row)
    for text,fn in [(t('اختيار السيارة','Choisir le véhicule','Select vehicle'),w.vehicle_page),(t('اتصال VCI','Connexion VCI','Connect VCI'),w.adapter_page)]:
        b=QPushButton(text);b.setObjectName('heroAction');b.clicked.connect(fn);row.addWidget(b)
    row.addStretch();body.addWidget(hero)
    metrics=QHBoxLayout();body.addLayout(metrics)
    for title,key in [(t('المحول','VCI','Adapter'),'adapter'),(t('تقارير محفوظة','Rapports enregistrés','Saved reports'),'reports'),(t('عملاء الورشة','Clients atelier','Workshop customers'),'customers')]:
        f=frame('metric');layout=QVBoxLayout(f);layout.setContentsMargins(18,14,18,14);layout.addWidget(label(title,'subtle'));value=label('—','metricValue');layout.addWidget(value);setattr(w,'metric_'+key,value);metrics.addWidget(f)
    body.addWidget(label(t('وصول سريع','Accès rapide','Quick access'),'sectionTitle'))
    grid=QGridLayout();grid.setSpacing(14);body.addLayout(grid);w.home_cards=[]
    cards=[('التشخيص الذكي','smart',w.diagnosis_page,'scan'),('المساعد الذكي','ai',w.ai_page,'ai'),('وظائف الصيانة','tools',w.service_page,'maintenance'),('قاعدة أكواد الأعطال','dtc',w.dtc_page,'dtc'),('سجل التشخيص','history',w.reports_page,'records'),('أوسيلوسكوب','live',w.scope_page,'scope')]
    for i,(name,art,fn,desc) in enumerate(cards):
        b=QPushButton();b.setObjectName('card');b.setMinimumHeight(120);b.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Preferred);b.clicked.connect(fn)
        layout=QVBoxLayout(b);layout.setContentsMargins(18,17,18,17);layout.setSpacing(8)
        top=QHBoxLayout();layout.addLayout(top);im=label('');im.setPixmap(icon(art).pixmap(36,36));im.setFixedSize(40,40);top.addWidget(im)
        title=label(tr(name),'cardlabel');top.addWidget(title,1);layout.addWidget(translated(desc,'subtle'))
        for q in b.findChildren(QLabel):q.setAttribute(Qt.WA_TransparentForMouseEvents)
        grid.addWidget(b,i//2,i%2);w.home_cards.append(b)
    for col in range(2):grid.setColumnStretch(col,1)
    body.addWidget(translated('hint','subtle'));body.addStretch();scroll.setWidget(home);w.pages.addWidget(scroll)
    footer=frame('footer');fl=QHBoxLayout(footer);fl.setContentsMargins(24,9,24,9);w.status=translated('offline','connection');fl.addWidget(w.status,1);fl.addWidget(label('GITM · PREVIEW','subtle'));w.layout.addWidget(footer)
    def state():
        v=w.vehicle;title=' · '.join(str(v.get(k,'')) for k in ['make','model','year'] if v.get(k))
        w.vehicle_summary.setText(title or t('لم تُحدد مركبة بعد','Aucun véhicule sélectionné','No vehicle selected yet'));w.session_label.setText(title or t('جلسة جديدة','Nouvelle session','New session'))
        connected=bool(transport.LINK.info().get('connected'));w.metric_adapter.setText(t('متصل','Connecté','Connected') if connected else t('غير متصل','Déconnecté','Disconnected'))
        try:
            with store.db() as c:w.metric_reports.setText(str(c.execute('SELECT count(*) FROM reports').fetchone()[0]))
            with wt.database() as c:w.metric_customers.setText(str(c.execute('SELECT count(*) FROM customers').fetchone()[0]))
        except Exception:w.metric_reports.setText('—');w.metric_customers.setText('—')
    w.session_timer=QTimer(w);w.session_timer.timeout.connect(state);w.session_timer.start(2500);state()
    def switch(index):
        change_language(['ar','fr','en'][index],w)
        for q,key in texts:
            if q is not w.status:q.setText(word(key))
        state()
    w.language_picker.currentIndexChanged.connect(switch)
    w.setStyleSheet('''
      QWidget {background:#f1f4f8;color:#182b43;font-family:Tajawal;font-size:15px;}
      QLabel {background:transparent;}
      QFrame#header,QFrame#footer {background:#ffffff;border-bottom:1px solid #dfe5ed;}
      QLabel#brand {color:#102d48;font-family:DejaVu Sans;font-size:20px;font-weight:700;}
      QLabel#session {color:#60728a;font-size:14px;}
      QFrame#sidebar,QScrollArea#sideScroll {background:#10263d;}
      QLabel#sideCaption {color:#93a8bf;font-size:11px;letter-spacing:1px;}
      QPushButton#navButton,QPushButton#sideTool {text-align:left;background:transparent;color:#c9d6e6;border:0;border-radius:9px;padding:10px 8px;min-height:26px;}
      QPushButton#navButton:hover,QPushButton#sideTool:hover {background:#203c58;color:#ffffff;}
      QPushButton#navButton:checked {background:#245581;color:#ffffff;}
      QLabel#welcome {font-size:28px;font-weight:700;}
      QLabel#heading {font-size:26px;font-weight:700;}
      QLabel#subtle,QLabel#connection {color:#65768b;font-size:14px;}
      QLabel#sectionTitle {font-size:19px;font-weight:700;}
      QFrame#hero {background:#163955;border-radius:15px;}
      QLabel#heroCaption {color:#9fbed7;font-size:13px;}
      QLabel#heroTitle {color:#ffffff;font-size:25px;font-weight:700;}
      QLabel#heroText {color:#bfd2e4;font-size:14px;}
      QPushButton#heroAction {background:#ffffff;color:#164367;border:0;}
      QFrame#metric {background:#ffffff;border:1px solid #e1e7ef;border-radius:12px;}
      QLabel#metricValue {font-size:22px;font-weight:700;color:#173955;}
      QPushButton {background:#186ab5;color:#ffffff;border:1px solid #186ab5;border-radius:8px;padding:9px 14px;min-height:24px;}
      QPushButton:hover {background:#12548f;}
      QPushButton:pressed {background:#103f6c;}
      QPushButton:disabled {background:#e8edf3;color:#77879a;border-color:#dde4ec;}
      QPushButton#card {background:#ffffff;color:#182b43;border:1px solid #e0e7ef;border-radius:12px;padding:0;}
      QPushButton#card:hover {background:#f8fbff;border:1px solid #81b0d8;}
      QLabel#cardlabel {font-size:18px;font-weight:700;}
      QLineEdit,QTextEdit,QTextBrowser,QComboBox,QListWidget {background:#ffffff;color:#182b43;border:1px solid #d8e1eb;border-radius:8px;padding:9px;selection-background-color:#186ab5;}
      QTableWidget {background:#ffffff;alternate-background-color:#f5f8fb;gridline-color:#e9eef4;border:1px solid #dce4ed;border-radius:8px;selection-background-color:#dcecff;selection-color:#163955;}
      QHeaderView::section {background:#eaf0f6;border:0;border-bottom:1px solid #dce4ed;padding:10px;color:#4c6179;font-weight:700;}
      QTableWidget::item {padding:9px;}
      QComboBox::drop-down {border:0;width:22px;}
      QScrollArea {border:0;background:transparent;}
      QScrollBar:vertical {background:#e8edf3;width:8px;border:0;} QScrollBar::handle:vertical {background:#b8c7d7;border-radius:4px;min-height:30px;}
      QToolTip {background:#10263d;color:white;padding:8px;border:0;}
    ''')
