"""SQLite history, preserving original records and acquisition provenance."""
import json
from html import escape
from PySide6.QtCore import Qt
from PySide6.QtGui import QTextDocument
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLineEdit,QComboBox,QTableWidget,QTableWidgetItem,QTextBrowser,QFileDialog,QLabel
from PySide6.QtPrintSupport import QPrinter,QPrintDialog
import store
from diagnostic_reports import html_report,write_report
from professional_components import triple,action_button,configure_table

def provenance(record):
 result=record.get('result')
 return result.get('evidence','unknown') if isinstance(result,dict) else 'unknown'

def filter_records(rows,query='',evidence='all'):
 return [r for r in rows if query.casefold() in json.dumps(r,ensure_ascii=False).casefold() and (evidence=='all' or provenance(r)==evidence)]

def is_session(report):return isinstance(report,dict) and report.get('format')=='gitm-obd-session/1'

def compare_reports(a,b):
 if not is_session(a) or not is_session(b):return triple('اختر جلستي OBD','Choisir deux sessions OBD','Select two OBD sessions')
 if a.get('evidence')!=b.get('evidence') or a.get('evidence') not in ('physical','physical-unverified'):return triple('دليل محاكاة أو مصدر غير معروف: المقارنة غير متاحة.','Preuve simulée ou provenance inconnue : comparaison indisponible.','Simulator / physical or unknown provenance: comparison unavailable.')
 lines=['Evidence: '+str(a.get('evidence','unknown'))+' · '+str(a.get('status','unknown'))+' → '+str(b.get('status','unknown'))]
 lines.append('Session '+str(a.get('id','unknown'))+' → '+str(b.get('id','unknown')))
 if a.get('vehicle')!=b.get('vehicle'):lines.append(triple('هوية السيارة مختلفة؛ لا تُعتبر متابعة إصلاح.','Identité différente ; ce n’est pas un suivi de réparation.','Vehicle identity differs: observations are not a repair follow-up.'))
 maps=[{e['id']:e for e in r.get('ecus',[])} for r in (a,b)]
 for ecu in sorted(set(maps[0])|set(maps[1])):
  for kind in ('stored','pending','permanent'):
   values=[m.get(ecu,{}).get('dtc',{}).get(kind,{}) for m in maps]
   if any(v.get('status')!='ok' for v in values):lines.append(f'{ecu} / {kind}: '+triple('قراءة مجهولة أو جزئية؛ لا يمكن تأكيد زوال العطل','Lecture inconnue ou partielle ; résolution non confirmée','unknown / partial acquisition; no resolution inferred'))
   else:
    left,right=[set(v.get('codes',[])) for v in values];lines.append(f'{ecu} / {kind}: '+triple('لم تُرصد مجدداً','Non observés à nouveau','Not observed again')+f' {sorted(left-right)}; '+triple('جديدة','Nouveaux','New')+f' {sorted(right-left)}; '+triple('مستمرة','Persistants','Retained')+f' {sorted(left&right)}')
 if not (maps[0] or maps[1]):lines.append(triple('مجهول: لا توجد قراءات ECU','Inconnu : aucune observation ECU','Unknown: no ECU observations'))
 return '\n'.join(lines)

class History(QWidget):
 def __init__(self,window):
  super().__init__();self.window=window;self.records=[];self.visible=[];layout=QVBoxLayout(self)
  row=QHBoxLayout();self.search=QLineEdit();self.search.setPlaceholderText(triple('بحث في السجل','Rechercher dans l’historique','Search history'));row.addWidget(self.search,1);self.scope=QComboBox()
  for text,value in [(triple('الكل','Tout','All'),'all'),(triple('محاكاة','Simulation','Simulator'),'simulator'),(triple('مصدر فعلي غير متحقق','Physique non vérifié','Physical source, unverified'),'physical-unverified'),(triple('غير معروف','Inconnu','Unknown'),'unknown')]:self.scope.addItem(text,value)
  row.addWidget(self.scope);layout.addLayout(row)
  self.table=QTableWidget(0,5);configure_table(self.table);self.table.setSelectionBehavior(QTableWidget.SelectRows);self.table.setSelectionMode(QTableWidget.ExtendedSelection);self.table.setHorizontalHeaderLabels(['ID',triple('الوقت','Date','Time'),triple('المركبة','Véhicule','Vehicle'),triple('العملية','Opération','Operation'),triple('الدليل','Preuve','Evidence')]);layout.addWidget(self.table,1)
  self.preview=QTextBrowser();layout.addWidget(self.preview,1);actions=QHBoxLayout();self.exports=[]
  for fmt in ('HTML','JSON','CSV','PDF',triple('طباعة','Imprimer','Print')):
   button=action_button(fmt);button.clicked.connect(lambda checked=False,f=fmt:self.export(f));actions.addWidget(button);self.exports.append(button)
  self.compare=action_button(triple('مقارنة جلستين','Comparer deux sessions','Compare two sessions'));self.compare.clicked.connect(self.comparison);actions.addWidget(self.compare);layout.addLayout(actions)
  self.feedback=QLabel();self.feedback.setWordWrap(True);layout.addWidget(self.feedback);self.search.textChanged.connect(self.filter);self.scope.currentIndexChanged.connect(self.filter);self.table.itemSelectionChanged.connect(self.selected)
  refresh=action_button(triple('تحديث السجل','Actualiser','Refresh'));refresh.clicked.connect(self.reload);row.addWidget(refresh);self.reload()
 def reload(self):
  try:self.records=store.reports();self.filter()
  except Exception as error:self.feedback.setText(str(error))
 def filter(self,*args):
  self.visible=filter_records(self.records,self.search.text(),self.scope.currentData());self.table.setRowCount(len(self.visible))
  for i,r in enumerate(self.visible):
   for j,v in enumerate((r['id'],r['time'],json.dumps(r['vehicle'],ensure_ascii=False),r['command'],provenance(r))):self.table.setItem(i,j,QTableWidgetItem(str(v)))
  self.selected();self.feedback.setText('' if self.visible else triple('لا توجد تقارير مطابقة','Aucun rapport correspondant','No matching reports'))
 def selection(self):return [self.visible[i.row()] for i in self.table.selectionModel().selectedRows()]
 def selected(self):
  rows=self.selection();report=rows[0]['result'] if len(rows)==1 else None
  self.preview.setHtml(html_report(report) if report and is_session(report) else '<pre>'+escape(json.dumps(rows,ensure_ascii=False,indent=2))+'</pre>')
  for button in self.exports:button.setEnabled(len(rows)==1)
  self.compare.setEnabled(len(rows)==2 and all(is_session(r['result']) for r in rows))
 def comparison(self):
  rows=self.selection()
  if len(rows)==2:self.preview.setPlainText(compare_reports(*(r['result'] for r in rows)))
 def export(self,fmt):
  rows=self.selection()
  if len(rows)!=1:return
  record=rows[0];report=record['result']
  try:
   if fmt not in ('HTML','JSON','CSV','PDF'):
    printer=QPrinter();dialog=QPrintDialog(printer,self)
    if dialog.exec():self.document(record).print_(printer)
    return
   path,_=QFileDialog.getSaveFileName(self,fmt,f'report-{record["id"]}.{fmt.lower()}',f'{fmt} (*.{fmt.lower()})')
   if not path:return
   if fmt=='PDF':
    printer=QPrinter();printer.setOutputFormat(QPrinter.PdfFormat);printer.setOutputFileName(path);self.document(record).print_(printer)
   elif fmt=='JSON':
    from pathlib import Path
    Path(path).write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
   elif is_session(report):write_report(path,report)
   else:raise ValueError(triple('هذا السجل متاح بصيغة JSON فقط','Ce relevé est disponible en JSON seulement','This legacy record is available as JSON only'))
   self.feedback.setText(path)
  except Exception as error:self.feedback.setText(str(error))
 def document(self,record):
  doc=QTextDocument();doc.setDefaultFont(self.font());doc.setHtml(html_report(record['result']) if is_session(record['result']) else '<pre>'+escape(json.dumps(record,ensure_ascii=False,indent=2))+'</pre>');return doc

def show(window):
 layout=window.page(triple('التقارير والسجل','Rapports et historique','Reports and history'));widget=History(window);layout.addWidget(widget);return widget
