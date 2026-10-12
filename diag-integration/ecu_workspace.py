"""Explicit, read-only native ECU profile acquisition; no shipped OEM definitions."""
import json
import re
from pathlib import Path
import ecu_scan
from transport import LINK

LIMIT = 256 * 1024

def parse_profile(raw):
    if not isinstance(raw, bytes) or not 0 < len(raw) <= LIMIT:
        raise ValueError('Profile file must be 1–256 KiB')
    try: profile = json.loads(raw)
    except (ValueError, UnicodeError) as exc: raise ValueError('Invalid profile JSON') from exc
    return ecu_scan.validate_profile(profile)

def match_vehicle(profile, vehicle):
    ecu_scan.validate_profile(profile)
    try: year = int(vehicle.get('year', 0))
    except (ValueError, TypeError) as exc: raise ValueError('Valid vehicle year required') from exc
    declared = profile['vehicle']
    if any(str(vehicle.get(k, '')).casefold() != declared[k].casefold() for k in ('make', 'model')) or year not in declared['years']:
        raise ValueError('Profile does not match selected make/model/year')
    if declared.get('engine') and vehicle.get('engine') != declared['engine']:
        raise ValueError('Engine must match the profile exactly')
    if not str(vehicle.get('engine', '')).strip(): raise ValueError('Enter the exact vehicle engine')
    return {**vehicle, 'year':year}

def run_scan(profile, vehicle, index, live, cancel):
    vehicle = match_vehicle(profile, vehicle)
    with LINK.lock:
        if cancel.is_set(): raise RuntimeError('Cancelled before acquisition')
        if LINK.family != 'elm': raise ValueError('Connect a compatible ELM/STN adapter first')
        if LINK.protocol is None:
            LINK.query('0100')
            number = LINK.query('ATDPN').strip().upper().removeprefix('A')
            if not re.fullmatch('[1-9]', number): raise ValueError('Unrecognized established protocol')
            LINK.protocol = int(number)
        if LINK.protocol != profile['bus']['protocol']: raise ValueError('Established CAN protocol does not match profile')
        if cancel.is_set(): raise RuntimeError('Cancelled before acquisition')
        # Legacy scan_profile blocks until completion. Never interrupt its I/O or
        # bypass its finally cleanup; hiding the page cancels only queued work.
        return ecu_scan.scan_profile(profile, vehicle, index, live)

WORDS = {
 'title':('قراءة وحدات ECU الموثقة','Lecture des calculateurs documentés','Documented ECU reads'),
 'scope':('قراءة فقط. تستلزم عناوين وتعريفات موثقة للسيارة؛ لا توجد تعريفات OEM جاهزة هنا.','Lecture seule. Adresses et définitions documentées nécessaires ; aucune définition OEM fournie.','Read only. Requires documented vehicle addresses and definitions; no OEM definitions are supplied.'),
 'unverified':('إقرار الملف بالتوثيق ليس اعتماداً مستقلاً من GITM ولا دليلاً على اختبار سيارة.','La déclaration du fichier ne constitue ni certification GITM ni preuve de test véhicule.','Profile author declarations are not independent GITM certification or proof of vehicle testing.'),
 'import':('استيراد ملف JSON موثق','Importer un profil JSON documenté','Import documented JSON profile'),
 'ids':('قراءة الهوية والأعطال','Lire identités et défauts','Read identification / DTCs'),
 'live':('قراءة DIDs الحية الموثقة','Lire les DIDs documentés','Read documented live DIDs'),
 'offline':('حالة المحركات غير المتصلة','État des moteurs hors ligne','Offline engine capabilities'),
 'idle':('استورد ملفاً؛ لا يبدأ أي اتصال أو قراءة تلقائياً','Importer un profil ; aucune connexion ni lecture automatique','Import a profile; no automatic connection or reads'),
 'loaded':('تم التحقق من بنية الملف فقط؛ اختر السيارة ثم ابدأ القراءة','Structure du profil validée uniquement ; sélectionner le véhicule puis lire','Profile structure checked only; select vehicle and explicitly start a read'),
 'busy':('طلب آخر جارٍ؛ انتظر انتهاءه','Une opération est en cours ; attendre sa fin','Another operation is running; wait for completion'),
 'finishing':('الطلب الحالي سينتهي ثم يستعيد إعدادات المحول','La requête en cours se terminera puis restaurera l’adaptateur','Current request will finish and restore the adapter'),
 'running':('جارٍ قراءة العناوين الموثقة','Lecture des adresses documentées','Reading documented addresses'),
 'complete':('انتهى الطلب؛ راجع الحالة لكل وحدة','Requête terminée ; vérifier chaque calculateur','Request finished; review each ECU status'),
 'all':('كل وحدات الملف','Tous les calculateurs du profil','All ECUs in profile'),
 'make':('الماركة','Marque','Make'),'model':('الموديل','Modèle','Model'),'year':('السنة','Année','Year'),'engine':('المحرك','Moteur','Engine'),
 'source':('المصدر','Source','Source'),'ecu':('وحدة ECU','Calculateur','ECU'),'status':('الحالة','État','Status'),'read':('القراءة','Lecture','Read'),'value':('القيمة / البيانات','Valeur / données','Value / data'),'error':('الخطأ / NRC','Erreur / NRC','Error / NRC'),
 'responded':('استجابة صالحة','Réponse valide','Valid response'),'responded_pending':('استجابة معلقة غير مكتملة','Réponse en attente non résolue','Unresolved pending response'),'responded_negative':('استجابة رفض','Réponse négative','Negative response'),'not_attempted':('لم تتم المحاولة','Non tenté','Not attempted'),'no_valid_response':('لا توجد استجابة صالحة','Aucune réponse valide','No valid response')
}

def text(key):
    from i18n import language
    return WORDS.get(key, (key,key,key))[{'ar':0,'fr':1,'en':2}.get(language(),2)]

def workspace_class():
    from PySide6.QtCore import QEvent
    from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QLabel,QPushButton,QLineEdit,QComboBox,QTableWidget,QTableWidgetItem,QTextEdit,QFileDialog
    from shiboken6 import isValid
    from diagnostic_workspace import Worker
    import engine_adapters
    class Workspace(QWidget):
        def __init__(self, window):
            super().__init__();self.window=window;self.profile=None;self.worker=None
            root=QVBoxLayout(self)
            for key in ('scope','unverified'):
                label=QLabel(text(key));label.setWordWrap(True);root.addWidget(label)
            bar=QHBoxLayout();root.addLayout(bar);self.actions=[]
            for key,fn in [('import',self.choose_profile),('ids',lambda:self.acquire(False)),('live',lambda:self.acquire(True)),('offline',self.offline)]:
                button=QPushButton(text(key));button.clicked.connect(fn);bar.addWidget(button);self.actions.append(button)
            form=QFormLayout();root.addLayout(form);self.fields={}
            for key in ('make','model','year','engine'):
                field=QLineEdit(str(window.vehicle.get(key,'')));self.fields[key]=field;form.addRow(text(key),field)
            self.selection=QComboBox();form.addRow(text('ecu'),self.selection)
            self.source=QLabel(text('source')+' —');self.source.setWordWrap(True);root.addWidget(self.source)
            self.status=QLabel(text('idle'));self.status.setWordWrap(True);root.addWidget(self.status)
            self.table=QTableWidget(0,6);self.table.setHorizontalHeaderLabels([text(k) for k in ('ecu','status','read','value','error','source')]);root.addWidget(self.table,1)
            self.details=QTextEdit();self.details.setReadOnly(True);self.details.setMaximumHeight(160);root.addWidget(self.details)
            self.actions[1].setEnabled(False);self.actions[2].setEnabled(False)
        def load_profile(self, raw):
            profile=parse_profile(raw) # All validation completes before mutating UI.
            self.profile=profile;self.selection.clear();self.selection.addItem(text('all'),None)
            for i,ecu in enumerate(profile['ecus']):self.selection.addItem(ecu['name']+' · '+ecu['tx_id']+' / '+ecu['rx_id'],i)
            declared=profile['vehicle']
            for key in ('make','model','engine'):self.fields[key].setText(str(declared.get(key,'')))
            self.fields['year'].setText(str(declared['years'][0]) if len(declared['years'])==1 else '')
            self.fields['year'].setPlaceholderText(', '.join(map(str,declared['years'])))
            self.source.setText(text('source')+' · '+profile['source']);self.status.setText(text('loaded'))
            self.details.setPlainText(json.dumps({'vehicle':declared,'bus':profile['bus'],'validation':text('unverified')},ensure_ascii=False,indent=2))
            self.table.setRowCount(0);self.actions[1].setEnabled(True);self.actions[2].setEnabled(True)
        def choose_profile(self):
            filename,_=QFileDialog.getOpenFileName(self,text('import'),'','JSON (*.json)')
            if filename:
                try:
                    with Path(filename).open('rb') as stream:self.load_profile(stream.read(LIMIT+1))
                except Exception as exc:self.status.setText(str(exc))
        def launch(self, fn, done):
            current=getattr(self.window,'task',None)
            if self.worker is not None or getattr(self.window,'_obd_worker',None) is not None or (current is not None and current.isRunning()):
                self.status.setText(text('busy'));return
            self.status.setText(text('running'))
            for button in self.actions:button.setEnabled(False)
            worker=Worker(fn,self.window);self.worker=worker;self.window._obd_worker=worker;window=self.window
            worker.result.connect(lambda result:done(result) if isValid(self) else None)
            worker.failure.connect(lambda error:self.status.setText(error) if isValid(self) else None)
            def finished():
                if getattr(window,'_obd_worker',None) is worker:window._obd_worker=None
                if isValid(self):
                    self.worker=None
                    for i,button in enumerate(self.actions):button.setEnabled(self.profile is not None or i in (0,3))
            worker.finished.connect(finished);worker.start()
        def acquire(self, live):
            try:
                if self.profile is None:raise ValueError(text('idle'))
                vehicle=match_vehicle(self.profile,{**self.window.vehicle,**{key:field.text().strip() for key,field in self.fields.items()}})
                index=self.selection.currentData()
                if live and index is None:raise ValueError('Select one ECU for documented live DIDs')
                if live and not self.profile['ecus'][index].get('live_data'):raise ValueError('Selected ECU has no documented live DIDs')
            except Exception as exc:self.status.setText(str(exc));return
            self.window.vehicle=vehicle;profile=self.profile
            def fn(cancel,progress):
                result=run_scan(profile,vehicle,index,live,cancel)
                import store
                store.save(vehicle,'ECU_PROFILE_READ',result)
                return result
            self.launch(fn,self.display)
        def display(self,result):
            rows=[]
            for ecu in result.get('units',[]):
                reads=ecu.get('reads',{})
                if not reads:rows.append([ecu.get('name'),text(ecu.get('status','no_valid_response')),'—','—',ecu.get('error',ecu.get('reason','')),result.get('profile_source','')])
                for name,value in reads.items():
                    content=value.get('value',value.get('text',value.get('dtcs',value.get('hex','—'))))
                    if isinstance(content,(dict,list)):content=json.dumps(content,ensure_ascii=False)
                    if 'unit' in value:content=str(content)+' '+value['unit']
                    rows.append([ecu.get('name'),text(value.get('status',ecu.get('status','no_valid_response'))),name,content,value.get('error',value.get('nrc',ecu.get('error',''))),result.get('profile_source','')])
            self.table.setRowCount(len(rows))
            for r,row in enumerate(rows):
                for c,value in enumerate(row):self.table.setItem(r,c,QTableWidgetItem(str(value if value is not None else '—')))
            self.table.resizeColumnsToContents();self.details.setPlainText(json.dumps(result,ensure_ascii=False,indent=2));self.status.setText(text('complete'))
        def offline(self):
            self.launch(lambda cancel,progress:engine_adapters.status(),lambda result:(self.details.setPlainText(json.dumps(result,ensure_ascii=False,indent=2)),self.status.setText(text('offline'))))
        def hideEvent(self,event):
            if self.worker is not None:
                self.worker.cancel.set();self.status.setText(text('finishing'))
            super().hideEvent(event)
    return Workspace

def show(window):
    layout=window.page(text('title'));workspace=workspace_class()(window);layout.addWidget(workspace);return workspace
