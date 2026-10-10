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
 'tools':('أدوات الورشة','Outils atelier','Workshop tools'),
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
    for f in (ROOT/'assets').glob('Tajawal-*.ttf'):QFontDatabase.addApplicationFont(str(f))
    w.design_scale=1
    texts=[]
    def label(key,obj=''):
        q=QLabel(word(key));q.setObjectName(obj);q.setWordWrap(True);texts.append((q,key));return q
    header=QWidget();header.setObjectName('appHeader')
    h=QHBoxLayout(header);h.setContentsMargins(24,16,24,16);h.setSpacing(14)
    brand=QLabel('GITM  AUTODIAG');brand.setObjectName('brand');brand.setLayoutDirection(Qt.LeftToRight);h.addWidget(brand);h.addStretch()
    w.language_picker=QComboBox();w.language_picker.addItems(['العربية','Français','English']);w.language_picker.setMinimumWidth(135)
    w.language_picker.setCurrentIndex({'ar':0,'fr':1,'en':2}[language()]);h.addWidget(w.language_picker)
    w.layout.addWidget(header)
    nav=QWidget();nav.setObjectName('appNav');n=QHBoxLayout(nav);n.setContentsMargins(24,8,24,8)
    for key,callback in [('home',w.go_home),('vehicle',w.vehicle_page),('diagnosis',w.diagnosis_page),('assistant',w.ai_page),('tools',w.more_page),('settings',w.settings_page)]:
        b=QPushButton(word(key));b.setObjectName('navButton');b.clicked.connect(callback);texts.append((b,key));n.addWidget(b)
    n.addStretch();w.layout.addWidget(nav)
    w.pages=QStackedWidget();w.layout.addWidget(w.pages,1)
    scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setFrameShape(QScrollArea.NoFrame)
    home=QWidget();home.setObjectName('home');body=QVBoxLayout(home);body.setContentsMargins(28,24,28,28);body.setSpacing(16)
    body.addWidget(label('workspace','welcome'));body.addWidget(label('intro','subtle'))
    entries=[
      ('اختيار السيارة','car',w.vehicle_page,'select'),
      ('التشخيص الذكي','smart',w.diagnosis_page,'scan'),
      ('التشخيص المحلي','vci',w.adapter_page,'adapter'),
      ('المساعد الذكي','ai',w.ai_page,'ai'),
      ('سجل التشخيص','history',w.reports_page,'records'),
      ('وظائف الصيانة','tools',w.service_page,'maintenance'),
      ('قاعدة أكواد الأعطال','dtc',w.dtc_page,'dtc'),
      ('التغطية','coverage',w.engines_page,'coverage'),
      ('مراجع الإصلاح','reports',w.sources_page,'references'),
      ('أوسيلوسكوب','live',w.scope_page,'scope'),
      ('OBDII والبيانات الحية','live',w.diagnosis_page,'scan'),
      ('مخطط ربط VCI','vci',w.wiring_page,'adapter')]
    grid=QGridLayout();grid.setSpacing(16);body.addLayout(grid);w.home_cards=[]
    for i,(name,key,fn,desc) in enumerate(entries):
        card=QPushButton();card.setObjectName('card');card.setAccessibleName(tr(name));card.clicked.connect(fn)
        card.setMinimumHeight(132);card.setMinimumWidth(210);card.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Preferred)
        box=QVBoxLayout(card);box.setContentsMargins(20,18,20,18);box.setSpacing(8)
        row=QHBoxLayout();im=QLabel();im.setStyleSheet("background:transparent");im.setPixmap(icon(key).pixmap(36,36));im.setFixedSize(40,40);row.addWidget(im)
        title=label('live_title' if name=='OBDII والبيانات الحية' else 'wiring_title') if name in ('OBDII والبيانات الحية','مخطط ربط VCI') else QLabel(tr(name));title.setObjectName('cardlabel');title.setWordWrap(True);row.addWidget(title,1);box.addLayout(row)
        caption=label(desc,'subtle');box.addWidget(caption)
        for q in card.findChildren(QLabel):q.setAttribute(Qt.WA_TransparentForMouseEvents)
        grid.addWidget(card,i//3,i%3);w.home_cards.append(card)
    for col in range(3):grid.setColumnStretch(col,1)
    body.addWidget(label('hint','subtle'));body.addStretch();scroll.setWidget(home);w.pages.addWidget(scroll)
    footer=QWidget();footer.setObjectName('appFooter');f=QHBoxLayout(footer);f.setContentsMargins(24,10,24,10)
    w.status=label('offline','connection');w.status.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Preferred);f.addWidget(w.status)
    brand_footer=QLabel('GITM AutoDiag');brand_footer.setStyleSheet('background:transparent');f.addWidget(brand_footer);w.layout.addWidget(footer)
    def switch(index):
        change_language(['ar','fr','en'][index],w)
        for widget,key in texts:
            # Preserve real connection/task state when changing language.
            if widget is not w.status:widget.setText(word(key))
    w.language_picker.currentIndexChanged.connect(switch)
    w.setStyleSheet('''
      QWidget {background:#f3f5f9;color:#15243b;font-family:Tajawal;font-size:16px;}
      QWidget#appHeader {background:#10243a;} #appHeader QLabel {background:transparent;color:#f7faff;}
      QLabel#brand {font-family:DejaVu Sans;font-size:23px;font-weight:700;}
      QWidget#appNav,QWidget#appFooter {background:#ffffff;border-bottom:1px solid #e2e8f0;}
      QLabel#welcome {font-size:30px;font-weight:700;} QLabel#heading {font-size:26px;font-weight:700;}
      QLabel#subtle {color:#596b82;background:transparent;font-size:15px;}
      QLabel#connection {background:transparent;color:#596b82;}
      QPushButton {background:#1468ba;color:#ffffff;border:1px solid #1468ba;border-radius:9px;padding:10px 16px;min-height:24px;}
      QPushButton:hover {background:#0d559b;border-color:#0d559b;}
      QPushButton:pressed {background:#0a427a;}
      QPushButton:focus {border:2px solid #319ad9;}
      QPushButton:disabled {background:#e4e9ef;color:#65748a;border-color:#d9e0e8;}
      QPushButton#navButton {background:transparent;color:#344860;border:1px solid transparent;}
      QPushButton#navButton:hover {background:#e9f2fb;color:#105b9d;}
      QPushButton#card {background:#ffffff;color:#15243b;border:1px solid #dce4ed;border-radius:14px;padding:0;}
      QPushButton#card:hover {background:#f7fbff;border:1px solid #70a8d6;}
      QPushButton#card:pressed {background:#eaf3fc;}
      QPushButton#card:focus {border:2px solid #1468ba;}
      QLabel#cardlabel {background:transparent;font-size:19px;font-weight:700;}
      QLineEdit,QTextEdit,QTextBrowser,QComboBox,QListWidget {background:#ffffff;color:#15243b;border:1px solid #c9d5e2;border-radius:8px;padding:9px;selection-background-color:#1468ba;}
      QLineEdit:focus,QTextEdit:focus {border-color:#1468ba;}
      QComboBox::drop-down {border:0;width:24px;}
      QScrollArea {border:0;} QToolTip {background:#10243a;color:white;padding:8px;border:0;}
    ''')
