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
