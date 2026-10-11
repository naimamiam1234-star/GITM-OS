"""Application-only workflows. Never invent vehicle coverage or execute AI commands."""
import html,json,re,types
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QLabel,QLineEdit,QPushButton,QHBoxLayout,QGridLayout,
 QComboBox,QTextBrowser,QScrollArea,QWidget)
import automotive_data,transport,store
from workshop_tools import t

def render(value):
    """Readable, escaped diagnostic results; nested records remain separate."""
    if isinstance(value,dict):
        return '<table width="100%" cellspacing="8">'+''.join('<tr><td width="25%"><b>'+html.escape(str(k).replace('_',' '))+'</b></td><td>'+render(v)+'</td></tr>' for k,v in value.items())+'</table>'
    if isinstance(value,list):return '<hr>'.join(render(v) for v in value) or '—'
    return html.escape(str(value)) if value is not None else '—'

def install(w):
    from native import Task
    def run_readable(self,fn,out):
        if self.task and self.task.isRunning():return
        out.setHtml('<p>'+t('جارٍ القراءة…','Lecture…','Reading…')+'</p>')
        task=Task(fn);self.task=task
        task.result.connect(lambda value:out.setHtml(render(value)))
        task.failure.connect(lambda error:out.setHtml('<h3>'+t('تعذر إكمال الطلب','Échec de la requête','Request could not complete')+'</h3><p>'+html.escape(error)+'</p>'))
        task.finished.connect(lambda:self.status.setText(t('المحول متصل','VCI connecté','VCI connected') if transport.LINK.info().get('connected') else t('المحول غير متصل','VCI déconnecté','VCI disconnected')))
        task.start()
    w.run=types.MethodType(run_readable,w)
    def diagnosis(self):
        l=self.page(t('جلسة تشخيص OBD','Session diagnostic OBD','OBD diagnostic session'))
        summary=QLabel(t('قراءة OBD العامة؛ ليست فحصًا شاملًا لكل الوحدات.','OBD générique; pas un scan de tous les calculateurs.','Generic OBD reading; not an all-module scan.'));l.addWidget(summary)
        row=QHBoxLayout();l.addLayout(row);panel=QWidget();grid=QGridLayout(panel);row.addWidget(panel,1)
        self.diagout=QTextBrowser();self.diagout.setObjectName('diagnosticResults');row.addWidget(self.diagout,2)
        actions=[(('هوية VIN','Identité VIN','VIN identity'),'VIN'),(('أكواد الأعطال','Codes défaut','Fault codes'),'DTC'),(('البيانات الحية','Données en direct','Live data'),'LIVE'),(('البيانات المجمدة','Données figées','Freeze frame'),'FREEZE'),(('جاهزية الانبعاثات','État antipollution','Emissions readiness'),'READINESS'),(('جهد التغذية','Tension','Supply voltage'),'POWER')]
        for i,(names,cmd) in enumerate(actions):
            b=QPushButton(t(*names));b.setMinimumHeight(65);b.clicked.connect(lambda checked=False,c=cmd:self.run(lambda:self.read(c),self.diagout));grid.addWidget(b,i//2,i%2)
        self.diagout.setHtml('<h3>'+t('ابدأ بالاتصال بالمحول','Connectez le VCI','Connect your adapter first')+'</h3><p>'+t('ستظهر هنا نتائج القراءة الفعلية.','Les résultats réels apparaîtront ici.','Actual reading results will appear here.')+'</p>')
        controls=QHBoxLayout();l.addLayout(controls)
        for text,fn in [(t('اتصال VCI','Connexion VCI','Connect VCI'),self.adapter_page),(t('بدء / إيقاف البث','Démarrer / arrêter','Start / stop live'),self.toggle_live),(t('مسح بعد الإصلاح','Effacer après réparation','Clear after repair'),self.clear_dtc)]:
            b=QPushButton(text);b.clicked.connect(fn);controls.addWidget(b)
    w.diagnosis_page=types.MethodType(diagnosis,w)
    def dtc(self):
        l=self.page(t('مرجع الأعطال','Référence des défauts','Fault reference'));row=QHBoxLayout();l.addLayout(row)
        code=QLineEdit();code.setPlaceholderText('P0300');code.setLayoutDirection(Qt.LeftToRight)
        make=QLineEdit(self.vehicle.get('make',''));make.setPlaceholderText(t('المصنع','Constructeur','Manufacturer'))
        search=QPushButton(t('بحث','Rechercher','Search'))
        for item in (code,make,search):row.addWidget(item)
        out=QTextBrowser();l.addWidget(out,1)
        out.setHtml('<h3>'+t('ابحث بالكود وسياق السيارة','Cherchez par code et véhicule','Search by code and vehicle context')+'</h3><p>'+t('التعريف المجتمعي يحتاج مطابقة ECU؛ لا يعني أن القطعة تالفة.','Vérifiez la correspondance ECU.','Verify ECU applicability; a code does not prove a failed part.')+'</p>')
        def lookup():self.run(lambda:automotive_data.dtc(code.text().strip(),make.text().strip()),out)
        search.clicked.connect(lookup);code.returnPressed.connect(lookup)
        ai=QPushButton(t('ناقش العطل مع المساعد','Analyser avec l’assistant','Discuss with assistant'));l.addWidget(ai)
        def discuss():self.assistant_seed=' '.join([code.text().strip(),make.text().strip(),self.vehicle.get('model','')]);self.ai_page()
        ai.clicked.connect(discuss)
    w.dtc_page=types.MethodType(dtc,w)
    def identity(self,selected=''):
        l=self.page(t('هوية المركبة','Identité du véhicule','Vehicle identity'))
        l.addWidget(QLabel(t('حدد السيارة ثم احفظها للجلسة. الاختيار لا يثبت دعم التشخيص.','Identifiez le véhicule; le choix ne garantit pas la couverture.','Identify your vehicle; selection does not establish diagnostic coverage.')))
        grid=QGridLayout();l.addLayout(grid)
        fields=[]
        for i,(name,value) in enumerate([(t('الماركة','Marque','Make'),selected),(t('الموديل','Modèle','Model'),''),(t('السنة','Année','Year'),''),(t('المحرك','Moteur','Engine'),''),('VIN','')]):
            field=QLineEdit(value);field.setPlaceholderText(name);grid.addWidget(QLabel(name),i,0);grid.addWidget(field,i,1);fields.append(field)
        feedback=QLabel();l.addWidget(feedback)
        def save():
            make,model,year,engine,vin=[f.text().strip() for f in fields]
            if not make or not model:feedback.setText(t('أدخل الماركة والموديل','Saisir marque et modèle','Enter make and model'));return
            if year and (not year.isdigit() or not 1900<=int(year)<=2100):feedback.setText(t('السنة غير صالحة','Année invalide','Invalid year'));return
            if vin and not re.fullmatch('[A-HJ-NPR-Z0-9]{17}',vin.upper()):feedback.setText(t('VIN يجب أن يكون 17 حرفًا صالحًا','VIN: 17 caractères valides','VIN must contain 17 valid characters'));return
            self.vehicle=dict(make=make,model=model,year=year,engine=engine,vin=vin.upper());store.cache('vehicle_selection',self.vehicle)
            feedback.setText(t('تم حفظ المركبة للجلسة','Véhicule enregistré','Vehicle saved for this session'))
        self.button(l,t('اعتماد المركبة','Confirmer le véhicule','Confirm vehicle'),save);l.addStretch()
    w.vehicle_details=types.MethodType(identity,w)
    def service(self):
        l=self.page(t('وظائف الصيانة','Fonctions entretien','Service functions'))
        l.addWidget(QLabel(t('كل إجراء يحتاج تعريفًا مطابقًا للسيارة وECU.','Chaque procédure exige une définition compatible.','Every procedure requires a matching vehicle and ECU definition.')))
        grid=QGridLayout();l.addLayout(grid)
        from visual_theme import icon
        for i,(ar,fr,en) in enumerate([('زيت المحرك','Vidange','Oil reset'),('فرامل كهربائية','Frein électrique','EPB'),('حساس المقود','Angle volant','SAS'),('بطارية','Batterie','BMS'),('تنفيس ABS','Purge ABS','ABS bleed'),('مرشح الجسيمات','Filtre particules','DPF'),('البخاخات','Injecteurs','Injectors'),('بوابة الخانق','Papillon','Throttle'),('ضغط الإطارات','Pression pneus','TPMS')]):
            b=QPushButton(t(ar,fr,en)+'\n'+t('غير متاح دون تعريف مختبر','Définition testée requise','Tested definition required'));b.setIcon(icon('tools'));b.setMinimumHeight(100);b.setEnabled(False);grid.addWidget(b,i//3,i%3)
        l.addStretch()
    w.service_page=types.MethodType(service,w)
    saved=store.cache('vehicle_selection')
    if isinstance(saved,dict):w.vehicle=saved

def fault_cards(value):
    esc=lambda value:html.escape(str(value or '—'))
    code=esc(value.get('code'));definitions=value.get('definitions',[])
    parts=['<h1 style="color:#153954">'+code+'</h1><p>'+t('تعريفات من المصادر المتاحة؛ طابقها مع ECU قبل اعتمادها.','Vérifiez la correspondance avec le calculateur.','Match these source definitions to the exact ECU before relying on them.')+'</p>']
    if not definitions:parts.append('<h3>'+t('لا يوجد تعريف مطابق','Aucune définition correspondante','No matching definition')+'</h3>')
    for item in definitions:
        desc=esc(item.get('description') or item.get('definition'))
        parts.append('<hr><h2 style="color:#185f97">'+desc+'</h2>')
        for names,key in [(('المصنع','Constructeur','Manufacturer'),'manufacturer'),(('الوحدة','Calculateur','ECU'),'ecu'),(('المصدر','Source','Source'),'source')]:
            if item.get(key):parts.append('<p><b>'+t(*names)+'</b> · '+esc(item[key])+'</p>')
        for names,key in [(('الأسباب الواردة في المصدر','Causes documentées','Source-listed causes'),'causes'),(('إجراءات الإصلاح الواردة','Réparations documentées','Source-listed repairs'),'repairs')]:
            v=item.get(key)
            if isinstance(v,str):
                try:v=json.loads(v)
                except ValueError:pass
            if v:parts.append('<h3>'+t(*names)+'</h3>'+render(v))
        parts.append('<p style="color:#748397">'+t('رمز العطل لا يثبت تلف قطعة. إذا لم يقدم المصدر أسبابًا أو اختبارات فلن نخترعها.','Un code ne prouve pas une pièce défectueuse.','A code is not proof of a failed part. Missing source tests are not invented.')+'</p>')
    return ''.join(parts)

_original_render=render
def render(value):
    if isinstance(value,dict) and 'definitions' in value and 'code' in value:return fault_cards(value)
    return _original_render(value)

# Workshop presentation stays local and uses the existing persistence schema.
def customers(w):
    from PySide6.QtWidgets import QTableWidget,QTableWidgetItem,QHeaderView,QFrame
    import workshop_tools as wt
    l=w.page(t('عملاء الورشة','Clients atelier','Workshop customers'))
    l.addWidget(QLabel(t('معلومات العميل ومركبته محفوظة محليًا.','Clients et véhicules conservés localement.','Customer and vehicle information stays local.')))
    row=QHBoxLayout();l.addLayout(row,1)
    panel=QFrame();panel.setMaximumWidth(300);form=__import__('PySide6.QtWidgets',fromlist=['QVBoxLayout']).QVBoxLayout(panel);form.setContentsMargins(14,18,14,18);form.setSpacing(12)
    form.addWidget(QLabel(t('إضافة عميل','Ajouter un client','Add customer')))
    fields=[]
    for text in [t('اسم العميل','Nom du client','Customer name'),t('الهاتف','Téléphone','Phone'),t('السيارة أو رقم اللوحة','Véhicule ou immatriculation','Vehicle or plate')]:
        form.addWidget(QLabel(text));field=QLineEdit();field.setPlaceholderText(text);form.addWidget(field);fields.append(field)
    button=QPushButton(t('حفظ العميل','Enregistrer le client','Save customer'));form.addWidget(button);feedback=QLabel();form.addWidget(feedback);form.addStretch();row.addWidget(panel,1)
    right=__import__('PySide6.QtWidgets',fromlist=['QVBoxLayout']).QVBoxLayout();row.addLayout(right,3)
    search=QLineEdit();search.setPlaceholderText(t('ابحث بالاسم أو الهاتف أو السيارة','Nom, téléphone ou véhicule','Search name, phone or vehicle'));right.addWidget(search)
    table=QTableWidget(0,4);table.setHorizontalHeaderLabels(['ID',t('الاسم','Nom','Name'),t('الهاتف','Téléphone','Phone'),t('المركبة','Véhicule','Vehicle')]);table.setEditTriggers(QTableWidget.NoEditTriggers);table.setAlternatingRowColors(True);table.verticalHeader().hide();table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch);table.setColumnWidth(0,50);right.addWidget(table,1)
    def refresh():
        with wt.database() as c:rows=c.execute('SELECT id,name,phone,vehicle FROM customers ORDER BY id DESC LIMIT 1000').fetchall()
        query=search.text().casefold();rows=[r for r in rows if query in ' '.join(str(v or '') for v in r).casefold()];table.setRowCount(len(rows))
        for i,values in enumerate(rows):
            for j,value in enumerate(values):table.setItem(i,j,QTableWidgetItem(str(value or '')))
        table.resizeRowsToContents()
    def save():
        name,phone,vehicle=[f.text().strip() for f in fields]
        if not name:feedback.setText(t('اسم العميل مطلوب','Nom requis','Customer name is required'));return
        with wt.database() as c:c.execute('INSERT INTO customers(name,phone,vehicle) VALUES(?,?,?)',(name,phone,vehicle))
        for f in fields:f.clear()
        feedback.setText(t('تم الحفظ','Enregistré','Saved'));refresh()
    search.textChanged.connect(refresh);button.clicked.connect(save);refresh()

_original_install=install
def install(w):
    _original_install(w)
    import workshop_tools as wt
    wt.customers=customers
    original_invoice=getattr(wt,'_gitm_original_invoice',wt.invoices);wt._gitm_original_invoice=original_invoice
    def invoice(window):
        from PySide6.QtWidgets import QTableWidget,QHeaderView,QComboBox
        original_invoice(window);p=window.pages.currentWidget();table=p.findChild(QTableWidget)
        if table:
            table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch);table.verticalHeader().hide();table.setAlternatingRowColors(True)
            p.layout().setStretch(p.layout().indexOf(table),1)
            for q in p.findChildren(QComboBox):q.setMaximumWidth(420)
    wt.invoices=invoice

_final_install=install
def install(w):
    _final_install(w)
    from pathlib import Path
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QDesktopServices
    from PySide6.QtWidgets import QVBoxLayout,QFrame,QTableWidget,QTableWidgetItem,QHeaderView
    original_sources=w.sources_page
    def sources(self):
        l=self.page(t('المعلومات والمراجع','Informations et références','Information & references'))
        l.addWidget(QLabel(t('مصادر واضحة وحالة تكامل معلنة؛ وجود المصدر لا يثبت تغطية السيارة.','Sources et état réel de l’intégration.','Sources with explicit integration status; listing a source does not establish vehicle coverage.')))
        scroll=QScrollArea();scroll.setWidgetResizable(True);container=QWidget();body=QVBoxLayout(container);body.setSpacing(12);scroll.setWidget(container);l.addWidget(scroll,1)
        for source in json.loads((Path(__file__).parent/'sources.json').read_text()):
            card=QFrame();card.setStyleSheet('QFrame{background:white;border:1px solid #dde5ed;border-radius:10px} QLabel{border:0}');layout=QVBoxLayout(card);layout.setContentsMargins(18,14,18,14)
            title=QLabel(source.get('name',''));title.setStyleSheet('font-size:19px;font-weight:bold');layout.addWidget(title)
            description=QLabel(source.get('status',''));description.setWordWrap(True);layout.addWidget(description)
            row=QHBoxLayout();layout.addLayout(row);row.addWidget(QLabel(t('التكامل مختبر','Intégration vérifiée','Integration verified') if source.get('integration_verified') else t('التكامل غير مثبت','Intégration non vérifiée','Integration not verified')),1)
            button=QPushButton(t('فتح المصدر','Ouvrir la source','Open source'));url=source.get('url','');button.setEnabled(url.startswith('https://'));button.clicked.connect(lambda checked=False,url=url:QDesktopServices.openUrl(QUrl(url)));row.addWidget(button);body.addWidget(card)
        body.addStretch();self.button(l,t('استيراد ومعلومات متقدمة','Import et détails avancés','Import & advanced details'),original_sources)
    w.sources_page=types.MethodType(sources,w)
    def reports(self):
        l=self.page(t('سجل جلسات الفحص','Historique diagnostic','Diagnostic session records'))
        records=store.reports();l.addWidget(QLabel(t('تقارير محفوظة محليًا من القراءات الفعلية.','Rapports locaux des lectures effectuées.','Local records from diagnostic readings.')))
        table=QTableWidget(len(records),4);table.setHorizontalHeaderLabels([t('التاريخ','Date','Date'),t('المركبة','Véhicule','Vehicle'),t('القراءة','Lecture','Reading'),'ID']);table.setEditTriggers(QTableWidget.NoEditTriggers);table.setSelectionBehavior(QTableWidget.SelectRows);table.verticalHeader().hide();table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch);l.addWidget(table,1)
        detail=QTextBrowser();detail.setMaximumHeight(200);l.addWidget(detail)
        if not records:detail.setHtml('<h3>'+t('لا توجد جلسات محفوظة بعد','Aucun rapport enregistré','No saved sessions yet')+'</h3><p>'+t('تظهر القراءات هنا بعد الفحص.','Les lectures apparaîtront après diagnostic.','Readings will appear here after a diagnostic session.')+'</p>')
        for i,r in enumerate(records):
            vehicle=r.get('vehicle',{});title=' '.join(str(vehicle.get(k,'')) for k in ['make','model'])
            for j,value in enumerate([r.get('time',''),title,r.get('command',''),r.get('id','')]):table.setItem(i,j,QTableWidgetItem(str(value)))
        table.cellClicked.connect(lambda row,col:detail.setHtml(render(records[row].get('result',{}))))
    w.reports_page=types.MethodType(reports,w)
