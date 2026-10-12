"""SQLite history, preserving original records and acquisition provenance."""
import json,os,base64
from html import escape
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QTextDocument,QImageReader
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLineEdit,QComboBox,QTableWidget,QTableWidgetItem,QTextBrowser,QFileDialog,QLabel,QTextEdit
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

MAX_IMAGE_BYTES=10*1024*1024
MAX_IMAGE_PIXELS=16_000_000

def annotation_directory(report_id):
 if type(report_id) is not int or report_id<1:raise ValueError('Invalid report identity')
 return store.BASE/'report-annotations'/str(report_id)

def private_write(path,data):
 path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
 os.chmod(path.parent,0o700);os.chmod(path.parent.parent,0o700)
 temporary=path.with_suffix(path.suffix+'.new');fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
 with os.fdopen(fd,'wb') as output:os.fchmod(output.fileno(),0o600);output.write(data)
 os.replace(temporary,path)

def load_annotation(report_id):
 path=annotation_directory(report_id)/'metadata.json'
 if not path.exists():return {'notes':'','image':None}
 if path.stat().st_size>128000:raise ValueError('Annotation metadata exceeds limit')
 value=json.loads(path.read_text(encoding='utf-8'))
 return {'notes':str(value.get('notes',''))[:16000],'image':value.get('image') if value.get('image') in ('image.png','image.jpeg','image.webp') else None}

def save_annotation(report_id,notes,image=None,replace_image=False):
 if len(notes)>16000:raise ValueError('Technician notes exceed 16000 characters')
 value=load_annotation(report_id);value['notes']=notes
 if replace_image:value['image']=image
 private_write(annotation_directory(report_id)/'metadata.json',json.dumps(value,ensure_ascii=False).encode())
 return value

def attach_image(report_id,path):
 path=Path(path)
 if not path.is_file() or path.stat().st_size>MAX_IMAGE_BYTES:raise ValueError('Image must be a local file of at most 10 MiB')
 reader=QImageReader(str(path));kind=bytes(reader.format()).decode('ascii','ignore').lower();size=reader.size()
 if kind not in ('png','jpeg','webp') or not size.isValid() or max(size.width(),size.height())>4096 or size.width()*size.height()>MAX_IMAGE_PIXELS:raise ValueError('Choose a valid PNG, JPEG or WebP image up to 4096 pixels per side')
 if reader.read().isNull():raise ValueError('Image could not be decoded')
 data=path.read_bytes()
 if len(data)>MAX_IMAGE_BYTES:raise ValueError('Image exceeds limit')
 directory=annotation_directory(report_id);metadata=load_annotation(report_id);name='image.'+kind
 private_write(directory/name,data);save_annotation(report_id,metadata['notes'],name,True)
 if metadata['image'] and metadata['image']!=name:(directory/metadata['image']).unlink(missing_ok=True)

def remove_attachment(report_id):
 value=load_annotation(report_id);save_annotation(report_id,value['notes'],None,True)
 if value['image']:(annotation_directory(report_id)/value['image']).unlink(missing_ok=True)

def record_html(record):
 report=record['result'];body=html_report(report) if is_session(report) else '<pre>'+escape(json.dumps(record,ensure_ascii=False,indent=2))+'</pre>'
 metadata=load_annotation(record['id']);extra='<h2>'+triple('ملاحظات الفني المضافة','Annotations du technicien','Added technician annotations')+'</h2><p>'+escape(metadata['notes']).replace('\n','<br>')+'</p>'
 if metadata['image']:
  path=annotation_directory(record['id'])/metadata['image']
  if path.is_file() and path.stat().st_size<=MAX_IMAGE_BYTES:
   kind=path.suffix[1:];extra+='<p><img width="600" src="data:image/'+kind+';base64,'+base64.b64encode(path.read_bytes()).decode()+'"></p>'
 return body.replace('</body>',extra+'</body>') if '</body>' in body else body+extra

class History(QWidget):
 def __init__(self,window):
  super().__init__();self.window=window;self.records=[];self.visible=[];layout=QVBoxLayout(self)
  row=QHBoxLayout();self.search=QLineEdit();self.search.setPlaceholderText(triple('بحث في السجل','Rechercher dans l’historique','Search history'));row.addWidget(self.search,1);self.scope=QComboBox()
  for text,value in [(triple('الكل','Tout','All'),'all'),(triple('محاكاة','Simulation','Simulator'),'simulator'),(triple('مصدر فعلي غير متحقق','Physique non vérifié','Physical source, unverified'),'physical-unverified'),(triple('غير معروف','Inconnu','Unknown'),'unknown')]:self.scope.addItem(text,value)
  row.addWidget(self.scope);layout.addLayout(row)
  self.table=QTableWidget(0,5);configure_table(self.table);self.table.setSelectionBehavior(QTableWidget.SelectRows);self.table.setSelectionMode(QTableWidget.ExtendedSelection);self.table.setHorizontalHeaderLabels(['ID',triple('الوقت','Date','Time'),triple('المركبة','Véhicule','Vehicle'),triple('العملية','Opération','Operation'),triple('الدليل','Preuve','Evidence')]);layout.addWidget(self.table,1)
  self.preview=QTextBrowser();self.preview.setStyleSheet("background:white;color:#163249");layout.addWidget(self.preview,1);self.notes=QTextEdit();self.notes.setMaximumHeight(75);self.notes.setPlaceholderText(triple('ملاحظات الفني؛ تحفظ منفصلة عن الفحص الأصلي','Notes conservées séparément du diagnostic original','Technician notes are saved separately from the original scan'));layout.addWidget(self.notes);annotation_actions=QHBoxLayout();self.save_notes=action_button(triple('حفظ الملاحظات','Enregistrer notes','Save notes'));self.save_notes.clicked.connect(lambda:self.annotate('notes'));annotation_actions.addWidget(self.save_notes);self.add_image=action_button(triple('إرفاق صورة','Joindre une image','Attach image'));self.add_image.clicked.connect(lambda:self.annotate('image'));annotation_actions.addWidget(self.add_image);self.remove_image=action_button(triple('إزالة الصورة','Retirer l’image','Remove image'));self.remove_image.clicked.connect(lambda:self.annotate('remove'));annotation_actions.addWidget(self.remove_image);layout.addLayout(annotation_actions);actions=QHBoxLayout();self.exports=[]
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
  metadata={'notes':'','image':None}
  try:
   if len(rows)==1:metadata=load_annotation(rows[0]['id'])
   self.preview.setHtml(record_html(rows[0]) if len(rows)==1 else '<pre>'+escape(json.dumps(rows,ensure_ascii=False,indent=2))+'</pre>')
  except Exception as error:self.feedback.setText(str(error))
  self.notes.setPlainText(metadata['notes']);self.notes.setEnabled(len(rows)==1);self.save_notes.setEnabled(len(rows)==1);self.add_image.setEnabled(len(rows)==1);self.remove_image.setEnabled(len(rows)==1 and bool(metadata['image']))
  for button in self.exports:button.setEnabled(len(rows)==1)
  self.compare.setEnabled(len(rows)==2 and all(is_session(r['result']) for r in rows))
 def annotate(self,action):
  rows=self.selection()
  if len(rows)!=1:return
  try:
   id=rows[0]['id'];draft=self.notes.toPlainText()
   if action=='notes':save_annotation(id,self.notes.toPlainText())
   elif action=='remove':remove_attachment(id)
   else:
    path,_=QFileDialog.getOpenFileName(self,triple('صورة محلية','Image locale','Local image'),'','Images (*.png *.jpg *.jpeg *.webp)')
    if not path:return
    attach_image(id,path)
   self.selected()
   if action!='notes':self.notes.setPlainText(draft)
   self.feedback.setText(triple('حُفظت الإضافة محلياً','Annotation enregistrée localement','Annotation saved locally'))
  except Exception as error:self.feedback.setText(str(error))
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
    Path(path).write_text(json.dumps({**record,'annotations':load_annotation(record['id'])},ensure_ascii=False,indent=2),encoding='utf-8')
   elif fmt=='HTML':Path(path).write_text(record_html(record),encoding='utf-8')
   elif is_session(report):write_report(path,report)
   else:raise ValueError(triple('هذا السجل متاح بصيغة JSON فقط','Ce relevé est disponible en JSON seulement','This legacy record is available as JSON only'))
   self.feedback.setText(path)
  except Exception as error:self.feedback.setText(str(error))
 def document(self,record):
  doc=QTextDocument();doc.setDefaultFont(self.font());doc.setHtml(record_html(record));return doc

def show(window):
 layout=window.page(triple('التقارير والسجل','Rapports et historique','Reports and history'));widget=History(window);layout.addWidget(widget);return widget
