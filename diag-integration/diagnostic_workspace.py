"""Native emissions OBD workspace. No simulated observations."""
import threading, json, re
from html import escape
from datetime import datetime, timezone
from collections import deque
from shiboken6 import isValid
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QEvent
from PySide6.QtGui import QPainter, QColor, QPen
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QTabWidget,QTableWidget,QTableWidgetItem,QTextEdit,QComboBox,QMessageBox,QFileDialog,QCheckBox
import transport, store
from i18n import language
from diagnostic_reports import html_report,write_report,export_csv
from obd_session import Session, PIDS

WORDS={
 'title':('تشخيص OBD','Diagnostic OBD','OBD diagnostics'), 'scan':('فحص','Analyser','Scan'), 'cancel':('إلغاء','Annuler','Cancel'), 'clear':('مسح الأعطال','Effacer les défauts','Clear DTCs'), 'connect':('المحول','Adaptateur','Adapter'), 'summary':('ملخص','Résumé','Summary'), 'live':('بيانات حية','Données en direct','Live data'), 'ready':('الجاهزية','Préparation','Readiness'), 'freeze':('الإطار المجمد','Trame figée','Freeze frame'), 'report':('تقرير','Rapport','Report'), 'export':('تصدير التقرير','Exporter le rapport','Export report'), 'record':('تسجيل CSV','Enregistrer CSV','Record CSV'), 'start':('بدء / إيقاف البيانات','Démarrer / arrêter','Start / stop live'), 'scope':('OBD الانبعاثات العام فقط؛ لا يشمل جميع وحدات السيارة.','OBD émissions générique uniquement ; pas tous les calculateurs.','Generic emissions OBD only; does not cover every vehicle module.'), 'idle':('جاهز للفحص؛ لا توجد نتائج بعد','Prêt ; aucune observation','Ready to scan; no observations yet'), 'confirm':('سيتم مسح الأعطال وبيانات الإطار المجمد وإعادة ضبط الجاهزية. هل تريد المتابعة؟','Effacer les défauts et les trames figées et réinitialiser les moniteurs ?','Clear fault codes and freeze frames and reset readiness monitors?'), 'busy':('طلب جارٍ','Opération en cours','Operation in progress'), 'full':('توقف التسجيل: حد 10000 سجل','Enregistrement arrêté : limite de 10000','Recording stopped: 10,000 record limit')}
WORDS.update({'stored':('مخزن','Mémorisé','Stored'),'pending':('معلق','En attente','Pending'),'permanent':('دائم','Permanent','Permanent'),'ok':('قراءة ناجحة','Lecture réussie','Read successful'),'error':('خطأ في القراءة','Erreur de lecture','Read error'),'yes':('نعم','Oui','Yes'),'no':('لا','Non','No'),'unsupported':('غير مدعوم','Non pris en charge','Unsupported'),'definition':('مرجع العطل المحدد','Référence du défaut sélectionné','Selected DTC reference'),'reference':('تعريف مرجعي محلي؛ ليس تأكيداً للسبب. تحقق من انطباقه على وحدة التحكم والسيارة.','Définition locale de référence ; cause non confirmée. Vérifier le calculateur et le véhicule.','Local reference definition; not a confirmed cause. Verify ECU and vehicle applicability.'),'selectcode':('اختر رمز عطل صالحاً من الجدول','Sélectionner un code valide dans le tableau','Select a valid DTC from the table'),'scanfirst':('افحص أولاً لاختيار بيانات مدعومة','Analyser avant de choisir les données','Scan first to select supported data'),'simulator':('محاكاة فقط — ليس دليل فحص سيارة فعلية','Simulation uniquement — aucune preuve de véhicule physique','Bench simulation only — not physical vehicle evidence'),'complete':('مكتمل','Terminé','Complete'),'partial':('جزئي','Partiel','Partial'),'cancelled':('ملغى','Annulé','Cancelled'),'connected':('متصل','Connecté','Connected'),'disconnected':('غير متصل','Déconnecté','Disconnected'),'nodata':('لا توجد بيانات','Aucune donnée','No data')})
HEADERS={
'transport':('الاتصال','Transport','Transport'),'target':('العنوان','Adresse','Endpoint'),'protocol_number':('رقم البروتوكول','Numéro du protocole','Protocol number'),'ECU':('وحدة التحكم','Calculateur','ECU'),'Class':('الفئة','Classe','Class'),'Status':('الحالة','État','Status'),'DTC / error':('العطل / الخطأ','Défaut / erreur','DTC / error'),'Time':('الوقت','Heure','Time'),'Name':('المعلمة','Paramètre','Name'),'Value':('القيمة','Valeur','Value'),'Unit':('الوحدة','Unité','Unit'),'Error':('خطأ','Erreur','Error'),'MIL':('مصباح العطل','Voyant MIL','MIL'),'DTC count':('عدد الأعطال','Nombre de défauts','DTC count'),'Monitor':('المراقب','Moniteur','Monitor'),'Supported':('مدعوم','Pris en charge','Supported'),'Complete':('مكتمل','Terminé','Complete'),'status':('الحالة','État','Status'),'vehicle':('السيارة','Véhicule','Vehicle'),'adapter':('المحول','Adaptateur','Adapter'),'protocol':('البروتوكول','Protocole','Protocol'),'scope':('النطاق','Périmètre','Scope'),'started_at':('بدأ في','Début','Started'),'finished_at':('انتهى في','Fin','Finished'),'Acquisition errors':('أخطاء الحصول على البيانات','Erreurs d’acquisition','Acquisition errors'),'ECUs / VIN':('وحدات التحكم / VIN','Calculateurs / VIN','ECUs / VIN'),'Unavailable':('غير متاح','Indisponible','Unavailable'),'Frame':('الإطار','Trame','Frame'),'Trigger DTC':('العطل المسبب','Défaut déclencheur','Trigger DTC')}
def h(key):return HEADERS.get(key,(key,key,key))[{'ar':0,'fr':1,'en':2}.get(language(),2)]
def t(key):return WORDS[key][{'ar':0,'fr':1,'en':2}.get(language(),2)]

def display_time(value,short=False):
 try:
  moment=datetime.fromisoformat(str(value).replace('Z','+00:00'))
  if moment.tzinfo is None:moment=moment.replace(tzinfo=timezone.utc)
  return moment.astimezone(timezone.utc).strftime('%H:%M:%S UTC' if short else '%Y-%m-%d %H:%M:%S UTC')
 except (ValueError,TypeError):return str(value or '—')
def display_bool(value):return t('yes') if value is True else t('no') if value is False else '—'

class Worker(QThread):
 result=Signal(object);failure=Signal(str);progress=Signal(str)
 def __init__(self,fn,parent):
  super().__init__(parent);self.cancel=threading.Event();self.fn=fn;parent.installEventFilter(self);self.finished.connect(self.deleteLater)
 def eventFilter(self,obj,event):
  if event.type()==QEvent.Close and self.isRunning():self.cancel.set();event.ignore();return True
  return super().eventFilter(obj,event)
 def run(self):
  try:self.result.emit(self.fn(self.cancel,self.progress.emit))
  except Exception as exc:self.failure.emit(str(exc))

class Graph(QWidget):
 def __init__(self):super().__init__();self.points=deque(maxlen=600);self.label="";self.setMinimumHeight(180)
 def paintEvent(self,event):
  p=QPainter(self);p.fillRect(self.rect(),QColor('#102436'));p.setPen(QColor('#cbd5e1'))
  p.drawText(12,20,self.label)
  if len(self.points)<2:p.drawText(self.rect(),Qt.AlignCenter,t('nodata'));return
  vals=list(self.points);lo=min(vals);hi=max(vals);span=hi-lo or 1
  left,top,right,bottom=60,46,self.width()-18,self.height()-30
  p.drawText(8,top+8,format(hi,'.5g'));p.drawText(8,bottom,format(lo,'.5g'));p.drawText(left,self.height()-8,str(len(vals))+' samples · 2 s target interval')
  p.setPen(QPen(QColor('#466076'),1));p.drawLine(left,top,left,bottom);p.drawLine(left,bottom,right,bottom)
  p.setPen(QPen(QColor('#39c6b4'),2))
  for i in range(1,len(vals)):
   p.drawLine(int(left+(i-1)*(right-left)/(len(vals)-1)),int(bottom-(vals[i-1]-lo)*(bottom-top)/span),int(left+i*(right-left)/(len(vals)-1)),int(bottom-(vals[i]-lo)*(bottom-top)/span))

class Workspace(QWidget):
 def __init__(self,window):
  super().__init__();self.window=window;self.session=Session(link=transport.LINK);self.connection_identity=self.connection_key();self.worker=None;self.report=None;self.samples=deque(maxlen=600);self.recorded=[];self.live_on=False
  window.installEventFilter(self);self.timer=QTimer(self);self.timer.setInterval(2000);self.timer.timeout.connect(self.poll)
  root=QVBoxLayout(self);root.addWidget(QLabel(t('scope')));self.connection=QLabel();root.addWidget(self.connection);self.refresh_connection()
  bar=QHBoxLayout();root.addLayout(bar);self.actions=[]
  for key,fn in [('connect',window.adapter_page),('scan',self.scan),('cancel',self.stop),('clear',self.clear),('export',self.export)]:
   b=QPushButton(t(key));b.clicked.connect(fn);bar.addWidget(b)
   if key!='cancel':self.actions.append(b)
  self.status=QLabel(t('idle'));root.addWidget(self.status);self.tabs=QTabWidget();root.addWidget(self.tabs,1)
  self.summary=QTextEdit();self.summary.setReadOnly(True);self.tabs.addTab(self.summary,t('summary'))
  self.dtc=self.table(['ECU','Class','Status','DTC / error']);dtc_page=QWidget();dtc_layout=QVBoxLayout(dtc_page);dtc_layout.addWidget(self.dtc,2);definition=QPushButton(t('definition'));definition.clicked.connect(self.lookup_dtc);dtc_layout.addWidget(definition);self.actions.append(definition);self.dtc_reference=QTextEdit();self.dtc_reference.setReadOnly(True);self.dtc_reference.setMaximumHeight(200);dtc_layout.addWidget(self.dtc_reference,1);self.dtc.cellDoubleClicked.connect(lambda row,col:self.lookup_dtc(row));self.tabs.addTab(dtc_page,'DTC')
  page=QWidget();l=QVBoxLayout(page);line=QHBoxLayout();l.addLayout(line);line.addWidget(QLabel(h('ECU')));self.ecus=QComboBox();line.addWidget(self.ecus);self.ecus.currentIndexChanged.connect(self.update_graph);self.pids=QComboBox();self.pids.currentIndexChanged.connect(self.update_graph);self.pids.setPlaceholderText(t('scanfirst'));line.addWidget(self.pids);b=QPushButton(t('start'));b.clicked.connect(self.toggle_live);line.addWidget(b);self.record=QCheckBox(t('record'));line.addWidget(self.record);b=QPushButton('CSV');b.clicked.connect(self.export_live);line.addWidget(b);self.graph=Graph();l.addWidget(self.graph);self.live_table=self.table(['Time','ECU','PID','Name','Value','Unit','Error']);self.live_table.setColumnWidth(0,150);l.addWidget(self.live_table);self.tabs.addTab(page,t('live'))
  self.ready=self.table(['ECU','MIL','DTC count','Monitor','Supported','Complete']);self.tabs.addTab(self.ready,t('ready'))
  self.freeze=self.table(['ECU','Frame','Trigger DTC','PID','Name','Value','Unit']);self.tabs.addTab(self.freeze,t('freeze'))
  self.report_view=QTextEdit();self.report_view.setReadOnly(True);self.tabs.addTab(self.report_view,t('report'))
 def table(self,headers):
  w=QTableWidget(0,len(headers));w.setHorizontalHeaderLabels([h(v) for v in headers]);w.setEditTriggers(QTableWidget.NoEditTriggers);w.horizontalHeader().setStretchLastSection(True);return w
 def rows(self,table,rows):
  table.setRowCount(len(rows))
  for i,row in enumerate(rows):
   for j,value in enumerate(row):table.setItem(i,j,QTableWidgetItem(str(value)))
 def connection_key(self):
  info=transport.LINK.info();return (id(transport.LINK),getattr(transport.LINK,'generation',0),info.get('connected'),info.get('transport'),info.get('target'),info.get('adapter'))
 def refresh_connection(self):
  try:
   info=transport.LINK.info();self.connection.setText(('● '+t('connected') if info.get('connected') else '○ '+t('disconnected'))+' · '+str(info.get('adapter') or '—')+' · '+str(info.get('target') or '—'))
   if hasattr(self.window,"status"):self.window.status.setText("GITM AutoDiag · "+self.connection.text())
  except Exception as e:self.connection.setText(str(e))
 def eventFilter(self,obj,event):
  if obj is self.window and event.type()==QEvent.Close and self.worker and self.worker.isRunning():self.stop();event.ignore();return True
  return super().eventFilter(obj,event)
 def hideEvent(self,event):self.stop();super().hideEvent(event)
 def stop(self):
  self.live_on=False;self.timer.stop()
  if self.worker:self.worker.cancel.set()
 def launch(self,fn,done):
  if self.worker is not None or getattr(self.window,'_obd_worker',None) is not None or (getattr(self.window,'task',None) is not None and self.window.task.isRunning()):return
  self.status.setText(t('busy'))
  for b in self.actions:b.setEnabled(False)
  self.worker=Worker(fn,self.window);self.window._obd_worker=self.worker;window=self.window;self.worker.finished.connect(lambda:setattr(window,'_obd_worker',None));self.worker.result.connect(lambda result:done(result) if isValid(self) else None);self.worker.failure.connect(lambda error:self.status.setText(error) if isValid(self) else None);self.worker.progress.connect(lambda message:self.status.setText(message) if isValid(self) else None);self.worker.finished.connect(lambda:self.finished() if isValid(self) else None);self.worker.start()
 def finished(self):
  w=self.worker;self.worker=None;w.deleteLater()
  for b in self.actions:b.setEnabled(True)
  self.refresh_connection()
 def scan(self):
  if self.worker is not None or getattr(self.window,'_obd_worker',None) is not None or (getattr(self.window,'task',None) is not None and self.window.task.isRunning()):return
  if self.recorded and self.report:
   try:store.save(self.report.get('vehicle',{}),'OBD_LIVE_RECORDING',{'session_id':self.report.get('id'),'evidence':self.report.get('evidence'),'samples':list(self.recorded)})
   except Exception as error:self.status.setText(str(error));return
  self.live_on=False;self.timer.stop();self.record.setChecked(False);self.samples.clear();self.recorded.clear();self.report=None
  for table in (self.live_table,self.dtc,self.ready,self.freeze):table.setRowCount(0)
  self.dtc_reference.clear();self.summary.clear();self.report_view.clear();self.ecus.clear();self.pids.clear();self.graph.points.clear();self.graph.label='';self.graph.update()
  identity=self.connection_key()
  if identity!=self.connection_identity:self.session=Session(link=transport.LINK);self.connection_identity=identity
  def fn(c,p):
   report=self.session.scan(vehicle=dict(self.window.vehicle),cancel=c,progress=p);store.save(self.window.vehicle,'OBD_SESSION',report);return report
  self.launch(fn,self.display)
 def display(self,report):
  selected_ecu=self.ecus.currentData();self.ecus.clear()
  for eid in sorted({str(e.get('id')) for e in report.get('ecus',[]) if e.get('id') is not None}):self.ecus.addItem(eid,eid)
  ecu_index=self.ecus.findData(selected_ecu);self.ecus.setCurrentIndex(ecu_index if ecu_index>=0 else (0 if self.ecus.count() else -1))
  self.report=report;self.status.setText(t(report.get('status','unknown')) if report.get('status') in WORDS else str(report.get('status','unknown')));selected=self.pids.currentData();self.pids.clear()
  supported=set().union(*(set(e.get('supported_pids',[])) for e in report.get('ecus',[])))
  for pid in sorted(supported.intersection(PIDS)):self.pids.addItem('%02X · %s · %s'%(pid,PIDS[pid][0],PIDS[pid][1]),pid)
  index=self.pids.findData(selected)
  self.pids.setCurrentIndex(index if index>=0 else (0 if self.pids.count() else -1))
  dtc=[];ready=[];freeze=[]
  for ecu in report.get('ecus',[]):
   eid=ecu.get('id','');r=ecu.get('readiness') or {};f=ecu.get('freeze') or {}
   for kind,data in (ecu.get('dtc') or {}).items():
    for code in data.get('codes',[]) or [data.get('error','—')]:dtc.append([eid,t(kind) if kind in WORDS else kind,t(data.get('status')) if data.get('status') in WORDS else data.get('status','unknown'),code])
   for m in r.get('monitors',[]):ready.append([eid,display_bool(r.get('MIL')),r.get('stored_dtc_count','—'),m.get('name'),display_bool(m.get('supported')),t('unsupported') if m.get('complete') is None else display_bool(m.get('complete'))])
   for v in f.get('values',[]):freeze.append([eid,f.get('frame'),', '.join(f.get('trigger_dtc',[])),v.get('pid'),v.get('name'),v.get('value'),v.get('unit')])
  self.rows(self.dtc,dtc);self.rows(self.ready,ready);self.rows(self.freeze,freeze)
  vehicle=report.get('vehicle') or {};adapter=report.get('adapter') or {}
  compact=lambda data:' · '.join(str(v) for v in data.values() if v not in (None,'',False)) if isinstance(data,dict) else str(data)
  status=report.get('status','unknown');status=t(status) if status in WORDS else str(status)
  overview={'vehicle':compact(vehicle),'adapter':' · '.join(h(k)+': '+str(adapter[k]) for k in ('adapter','transport','target','protocol_number') if adapter.get(k) is not None),'protocol':report.get('protocol'),'started_at':display_time(report.get('started_at')),'finished_at':display_time(report.get('finished_at'))}
  if report.get('clear_action'):overview['clear_action']=compact(report['clear_action'])
  self.summary.setHtml(('<h2 style="color:#b45309">SIMULATOR · '+escape(t('simulator'))+'</h2>' if report.get('evidence')=='simulator' else '')+'<h2>'+escape(status)+'</h2><p>'+escape(t('scope'))+'</p><table cellspacing=6>'+''.join('<tr><th align=left>'+escape(h(str(k)))+'</th><td>'+escape(str(v))+'</td></tr>' for k,v in overview.items())+'</table><h3>'+escape(h('ECUs / VIN'))+'</h3>'+''.join('<p>'+escape(str(e.get('id')))+' · '+escape(str(e.get('vin') or h('Unavailable')))+'<br>'+escape('; '.join(e.get('errors',[])))+'</p>' for e in report.get('ecus',[]))+'<h3>'+escape(h('Acquisition errors'))+'</h3>'+''.join('<p>'+escape(str(e.get('section','')))+' · '+escape(str(e.get('error','')))+'</p>' for e in report.get('errors',[])))
  self.report_view.setHtml(html_report(report))
 def clear(self):
  if QMessageBox.question(self,t('clear'),t('confirm'),QMessageBox.Yes|QMessageBox.No,QMessageBox.No)!=QMessageBox.Yes:return
  self.live_on=False;self.timer.stop()
  def fn(c,p):
   return self.session.clear(confirm=True,vehicle=dict(self.window.vehicle),cancel=c)
  def done(result):
   report=dict(result['after']);report['errors']=list(report.get('errors',[]))
   report['clear_action']={'acknowledgements':result.get('acknowledgements',[]),'scope':result.get('verification_scope'),'status':result.get('status'),'trace':result.get('trace',[]),'before_id':result.get('before',{}).get('id')}
   for error in result.get('errors',[]):report['errors'].append(dict(error,section='clear-operation') if isinstance(error,dict) else {'section':'clear-operation','error':str(error)})
   if result.get('status')!='verified':
    report['status']='partial'
    if not result.get('errors'):report['errors'].append({'section':'clear-operation','error':'Clear verification incomplete; acknowledgements or post-check are uncertain'})
   self.display(report);self.status.setText(t(report['status']) if report.get('status') in WORDS else str(report.get('status')))

  self.launch(fn,done)
 def toggle_live(self):
  self.live_on=not self.live_on
  if self.live_on:self.timer.start();self.poll()
  else:self.timer.stop()
 def poll(self):
  if not self.isVisible():self.stop();return
  if self.worker is not None:return
  if self.connection_key()!=self.connection_identity:self.stop();self.pids.clear();self.session=Session(link=transport.LINK);self.status.setText(t('scanfirst'));return
  pid=self.pids.currentData()
  if pid is None:self.status.setText(t('scanfirst'));return
  def fn(c,p):
   return self.session.live(pids=[pid],cancel=c)
  self.launch(fn,self.live_result)
 def live_result(self,records):
  for raw in records:
   r=dict(raw,session_id=(self.report or {}).get('id'),vehicle=dict((self.report or {}).get('vehicle') or {}),evidence=(self.report or {}).get('evidence'))
   self.samples.append(r)
   if self.record.isChecked():
    if len(self.recorded)<10000:self.recorded.append(r)
    if len(self.recorded)>=10000:self.record.setChecked(False);self.status.setText(t('full'))
  self.rows(self.live_table,[[display_time(r.get('at'),short=True)]+[r.get(k,'—') for k in ('ecu','pid','name','value','unit','error')] for r in self.samples])
  self.update_graph()
  ecu=self.ecus.currentData();latest=[r for r in records if r.get('ecu')==ecu and r.get('pid')==self.pids.currentData()]
  message=next((str(r['error']) for r in latest if r.get('error')),t('nodata') if not latest else t('live'))
  self.status.setText(t('full') if len(self.recorded)>=10000 else str(ecu or '—')+' · '+message)
 def update_graph(self,*args):
  if not hasattr(self,'graph'):return
  ecu=self.ecus.currentData();pid=self.pids.currentData();self.graph.label=str(ecu or '—')+' · '+self.pids.currentText()
  self.graph.points.clear();self.graph.points.extend(r['value'] for r in self.samples if r.get('ecu')==ecu and r.get('pid')==pid and isinstance(r.get('value'),(int,float)));self.graph.update()
 def lookup_dtc(self,row=None):
  if isinstance(row,bool) or row is None:row=self.dtc.currentRow() if self.dtc.selectedItems() else -1
  item=self.dtc.item(row,3) if row>=0 else None;code=item.text().strip().upper() if item else ''
  if not re.fullmatch(r'[PBCU][0-9A-F]{4}',code):self.dtc_reference.setPlainText(t('selectcode'));return
  make=str(self.window.vehicle.get('make',''))
  def fn(cancel,progress):
   import automotive_data
   return automotive_data.dtc(code,make)
  def done(result):
   definitions=result.get('definitions',[]);body='<h3>'+escape(code)+'</h3><p><strong>'+escape(t('reference'))+'</strong></p>'
   for definition in definitions:
    body+='<p>'+escape(str(definition.get('definition') or definition.get('description') or h('Unavailable')))+'</p><p>'+escape(str(definition.get('manufacturer','')))+' · '+escape(str(definition.get('ecu','')))+'<br>'+escape(str(definition.get('source','')))+' · '+escape(str(definition.get('source_file','')))+'<br>'+escape(str(definition.get('applicability',h('Unavailable'))))+'</p><hr>'
   if not definitions:body+='<p>'+escape(t('nodata'))+'</p>'
   self.dtc_reference.setHtml(body);self.status.setText(t('definition')+' · '+code)
  self.launch(fn,done)

 def export(self):
  if not self.report:return
  path,_=QFileDialog.getSaveFileName(self,t('export'),'obd-report.html','HTML (*.html);;JSON (*.json)')
  if path:
   try:write_report(path,dict(self.report,live=self.recorded or list(self.samples)))
   except Exception as e:self.status.setText(str(e))
 def export_live(self):
  path,_=QFileDialog.getSaveFileName(self,'CSV','obd-live.csv','CSV (*.csv)')
  if path:
   try:
    from pathlib import Path
    Path(path).write_text(export_csv(self.recorded or list(self.samples)),encoding='utf-8')
   except Exception as e:self.status.setText(str(e))
def show(window):
 layout=window.page(t('title'));workspace=Workspace(window);layout.addWidget(workspace);return workspace
