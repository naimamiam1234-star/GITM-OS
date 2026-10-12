"""Local workshop records. Tax is manually configured; historical snapshots are immutable."""
import json,datetime,decimal,os
from pathlib import Path
from html import escape
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QLineEdit,QTextEdit,QTextBrowser,QComboBox,QTableWidget,QTableWidgetItem,QDialog,QDialogButtonBox,QLabel,QMessageBox,QFileDialog,QDoubleSpinBox
from PySide6.QtGui import QTextDocument
from PySide6.QtPrintSupport import QPrinter,QPrintDialog
import store,workshop_tools
from professional_components import triple,action_button,configure_table
D=decimal.Decimal

def database():
 c=workshop_tools.database()
 additions={'customers':{'vehicles':"TEXT DEFAULT '[]'",'notes':"TEXT DEFAULT ''",'next_maintenance':"TEXT DEFAULT ''",'deleted':'INTEGER DEFAULT 0'},'invoices':{'status':"TEXT DEFAULT 'unknown'",'vehicle_snapshot':"TEXT DEFAULT '{}'",'discount':"TEXT DEFAULT '0.00'",'tax_rate':"TEXT DEFAULT '0'",'tax':"TEXT DEFAULT '0.00'",'subtotal':"TEXT DEFAULT ''",'legal_fields':"TEXT DEFAULT '{}'",'report_snapshot':"TEXT DEFAULT '{}'"}}
 for table,fields in additions.items():
  existing={r[1] for r in c.execute(f'PRAGMA table_info({table})')}
  for name,kind in fields.items():
   if name not in existing:c.execute(f'ALTER TABLE {table} ADD COLUMN {name} {kind}')
 c.commit();return c

def number(value):
 try:n=D(str(value))
 except decimal.InvalidOperation:raise ValueError('Invalid decimal value')
 if not n.is_finite() or n<0 or n>D('100000000'):raise ValueError('Value outside supported range')
 return n

def money(value):return value.quantize(D('.01'),rounding=decimal.ROUND_HALF_UP)

def calculate(lines,discount='0',tax_rate='0'):
 subtotal=sum((money(number(r['qty'])*number(r['price'])) for r in lines),D(0));discount=money(number(discount));rate=number(tax_rate)
 if discount>subtotal or rate>100:raise ValueError('Discount exceeds subtotal or tax rate exceeds 100%')
 net=subtotal-discount;tax=money(net*rate/D(100))
 return {k:format(v,'f') for k,v in {'subtotal':money(subtotal),'discount':discount,'net':money(net),'tax_rate':rate,'tax':tax,'total':money(net+tax)}.items()}

def customer_rows(query=''):
 with database() as c:
  c.row_factory=__import__('sqlite3').Row
  rows=[dict(r) for r in c.execute('SELECT *, (SELECT MAX(date) FROM invoices WHERE customer_id=customers.id) AS last_visit FROM customers WHERE deleted=0 ORDER BY name')]
 return [r for r in rows if query.casefold() in json.dumps(r,ensure_ascii=False).casefold()]

def vehicles(row):
 values=json.loads(row.get('vehicles') or '[]')
 return values or ([{'description':row['vehicle']}] if row.get('vehicle') else [])

def save_customer(id,data):
 name=data.get('name','').strip()
 if not name:raise ValueError(triple('اسم العميل مطلوب','Nom du client requis','Customer name is required'))
 vs=data.get('vehicles',[])
 if not isinstance(vs,list) or any(not isinstance(v,dict) for v in vs):raise ValueError('Vehicles must be a list of objects')
 date=data.get('next_maintenance','').strip()
 if date:datetime.date.fromisoformat(date)
 summary=' · '.join(str(v) for v in vs[0].values() if v) if vs else ''
 args=(name,data.get('phone',''),summary,json.dumps(vs,ensure_ascii=False),data.get('notes',''),date)
 with database() as c:
  if id is None:return c.execute('INSERT INTO customers(name,phone,vehicle,vehicles,notes,next_maintenance) VALUES(?,?,?,?,?,?)',args).lastrowid
  c.execute('UPDATE customers SET name=?,phone=?,vehicle=?,vehicles=?,notes=?,next_maintenance=? WHERE id=? AND deleted=0',args+(id,));return id

def remove_customer(id):
 with database() as c:c.execute('UPDATE customers SET deleted=1 WHERE id=?',(id,))

def save_invoice(customer_id,vehicle,lines,discount='0',tax_rate='0',status='draft',legal=None,report=None):
 if status not in ('draft','unpaid','paid','cancelled'):raise ValueError('Invalid invoice status')
 if not lines or any(not r.get('description','').strip() or number(r['qty'])==0 or r.get('category','services') not in ('parts','labor','services') for r in lines):raise ValueError('Describe every line and enter a positive quantity')
 totals=calculate(lines,discount,tax_rate)
 with database() as c:
  c.row_factory=__import__('sqlite3').Row;row=c.execute('SELECT * FROM customers WHERE id=? AND deleted=0',(customer_id,)).fetchone()
  if row is None:raise ValueError('Select an active customer')
  snapshot={'name':row['name'],'phone':row['phone'],'vehicle':vehicle}
  return c.execute('INSERT INTO invoices(date,customer_id,customer,lines,total,currency,status,vehicle_snapshot,discount,tax_rate,tax,subtotal,legal_fields,report_snapshot) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(datetime.date.today().isoformat(),customer_id,json.dumps(snapshot,ensure_ascii=False),json.dumps(lines,ensure_ascii=False),totals['total'],'MAD',status,json.dumps(vehicle,ensure_ascii=False),totals['discount'],totals['tax_rate'],totals['tax'],totals['subtotal'],json.dumps(legal or {},ensure_ascii=False),json.dumps(report or {},ensure_ascii=False))).lastrowid

def private_json(path,value):
 fd=os.open(str(path),os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
 try:
  os.fchmod(fd,0o600)
  with os.fdopen(fd,'w',encoding='utf-8') as output:json.dump(value,output,ensure_ascii=False,indent=2)
 except Exception:
  try:os.close(fd)
  except OSError:pass
  raise

class CustomerDialog(QDialog):
 def __init__(self,parent,row=None):
  super().__init__(parent);self.setWindowTitle(triple('بيانات العميل','Données client','Customer details'));self.resize(600,440);layout=QVBoxLayout(self);form=QFormLayout();layout.addLayout(form);row=row or {};self.fields={}
  for key,title in [('name',triple('الاسم','Nom','Name')),('phone',triple('الهاتف','Téléphone','Phone')),('next_maintenance',triple('الصيانة المقبلة YYYY-MM-DD','Prochaine maintenance YYYY-MM-DD','Next maintenance YYYY-MM-DD'))]:
   field=QLineEdit(str(row.get(key) or ''));self.fields[key]=field;form.addRow(title,field)
  self.notes=QTextEdit(str(row.get('notes') or ''));self.notes.setMaximumHeight(90);form.addRow(triple('ملاحظات الفني','Notes technicien','Technician notes'),self.notes)
  self.vehicles=QTableWidget(0,5);self.vehicles.setHorizontalHeaderLabels([triple('الشركة','Marque','Make'),triple('الموديل','Modèle','Model'),triple('السنة','Année','Year'),triple('المحرك','Moteur','Engine'),'VIN']);layout.addWidget(self.vehicles)
  for v in vehicles(row):self.add_vehicle(v)
  add=action_button(triple('إضافة مركبة','Ajouter véhicule','Add vehicle'));add.clicked.connect(lambda:self.add_vehicle({}));layout.addWidget(add);remove=action_button(triple('حذف المركبة المحددة','Retirer le véhicule sélectionné','Remove selected vehicle'));remove.clicked.connect(lambda:self.vehicles.removeRow(self.vehicles.currentRow()) if self.vehicles.currentRow()>=0 else None);layout.addWidget(remove);self.error=QLabel();layout.addWidget(self.error);buttons=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel);buttons.accepted.connect(self.validate);buttons.rejected.connect(self.reject);layout.addWidget(buttons)
 def add_vehicle(self,v):
  i=self.vehicles.rowCount();self.vehicles.insertRow(i)
  for j,k in enumerate(('make','model','year','engine','vin')):self.vehicles.setItem(i,j,QTableWidgetItem(str(v.get(k,v.get('description','') if j==0 else ''))))
 def data(self):
  vs=[{k:self.vehicles.item(i,j).text().strip() for j,k in enumerate(('make','model','year','engine','vin'))} for i in range(self.vehicles.rowCount())]
  return {**{k:w.text() for k,w in self.fields.items()},'notes':self.notes.toPlainText(),'vehicles':[v for v in vs if any(v.values())]}
 def validate(self):
  try:
   data=self.data()
   if not data['name'].strip():raise ValueError(triple('الاسم مطلوب','Nom requis','Name is required'))
   if data['next_maintenance']:datetime.date.fromisoformat(data['next_maintenance'])
   self.accept()
  except ValueError as error:self.error.setText(str(error))

class Customers(QWidget):
 def __init__(self,window):
  super().__init__();self.window=window;layout=QVBoxLayout(self);row=QHBoxLayout();self.search=QLineEdit();self.search.setPlaceholderText(triple('بحث العميل أو المركبة','Rechercher client ou véhicule','Search customer or vehicle'));self.search.textChanged.connect(self.refresh);row.addWidget(self.search,1)
  for title,callback in [(triple('إضافة','Ajouter','Add'),lambda:self.edit(False)),(triple('تعديل','Modifier','Edit'),lambda:self.edit(True)),(triple('أرشفة','Archiver','Archive'),self.archive),(triple('نسخة JSON','Sauvegarde JSON','JSON backup'),self.backup)]:
   b=action_button(title);b.clicked.connect(callback);row.addWidget(b)
  layout.addLayout(row);split=QHBoxLayout();self.table=QTableWidget(0,4);configure_table(self.table);self.table.setHorizontalHeaderLabels(['ID',triple('الاسم','Nom','Name'),triple('الهاتف','Téléphone','Phone'),triple('آخر فاتورة','Dernière facture','Last invoice')]);self.table.itemSelectionChanged.connect(self.details);split.addWidget(self.table,1);self.detail=QTextBrowser();split.addWidget(self.detail,1);layout.addLayout(split,1);self.feedback=QLabel();self.feedback.setWordWrap(True);layout.addWidget(self.feedback);self.refresh()
 def selected(self):
  row=self.table.currentRow();return self.rows[row] if 0<=row<len(self.rows) else None
 def refresh(self,*args):
  self.rows=customer_rows(self.search.text());self.table.setRowCount(len(self.rows))
  for i,r in enumerate(self.rows):
   for j,key in enumerate(('id','name','phone','last_visit')):self.table.setItem(i,j,QTableWidgetItem(str(r.get(key) or '—')))
  self.details()
 def details(self):
  row=self.selected()
  if not row:self.detail.setPlainText(triple('اختر عميلاً أو أضف سجلاً','Sélectionner ou ajouter un client','Select or add a customer'));return
  vehicle_html=''.join('<li>'+escape(' · '.join(str(v) for v in car.values() if v))+'</li>' for car in vehicles(row))
  self.detail.setHtml('<h2>'+escape(row['name'])+'</h2><p>'+escape(str(row.get('phone') or '—'))+'</p><h3>'+triple('المركبات','Véhicules','Vehicles')+'</h3><ul>'+vehicle_html+'</ul><p>'+triple('آخر فاتورة','Dernière facture','Last invoice')+': '+escape(str(row.get('last_visit') or '—'))+'</p><p>'+triple('الصيانة المقبلة','Prochaine maintenance','Next maintenance')+': '+escape(str(row.get('next_maintenance') or '—'))+'</p><h3>'+triple('ملاحظات الفني','Notes technicien','Technician notes')+'</h3><p>'+escape(str(row.get('notes') or '—')).replace('\n','<br>')+'</p>')
 def edit(self,existing):
  row=self.selected() if existing else None
  if existing and not row:return
  dialog=CustomerDialog(self,row)
  if dialog.exec():
   try:save_customer(row['id'] if row else None,dialog.data());self.refresh()
   except Exception as error:self.feedback.setText(str(error))
 def archive(self):
  row=self.selected()
  if row and QMessageBox.question(self,'GITM',triple('أرشفة العميل؟ تبقى الفواتير التاريخية محفوظة.','Archiver ce client ? Les factures historiques sont conservées.','Archive this customer? Historical invoices are retained.'))==QMessageBox.Yes:remove_customer(row['id']);self.refresh()
 def backup(self):
  path,_=QFileDialog.getSaveFileName(self,'JSON','workshop-backup.json','JSON (*.json)')
  if not path:return
  try:
   with database() as c:
    c.row_factory=__import__('sqlite3').Row;data={t:[dict(r) for r in c.execute('SELECT * FROM '+t)] for t in ('customers','invoices')}
   private_json(path,data);self.feedback.setText(path)
  except Exception as error:self.feedback.setText(str(error))

class InvoiceEditor(QWidget):
 def __init__(self,window):
  super().__init__();self.window=window;layout=QVBoxLayout(self);form=QFormLayout();self.customer=QComboBox();self.vehicle=QComboBox()
  for row in customer_rows():self.customer.addItem(row['name'],row)
  self.customer.currentIndexChanged.connect(self.change_customer);form.addRow(triple('العميل','Client','Customer'),self.customer);form.addRow(triple('المركبة','Véhicule','Vehicle'),self.vehicle);self.status=QComboBox()
  for text,value in [(triple('مسودة','Brouillon','Draft'),'draft'),(triple('غير مدفوعة','Impayée','Unpaid'),'unpaid'),(triple('مدفوعة','Payée','Paid'),'paid'),(triple('ملغاة','Annulée','Cancelled'),'cancelled')]:self.status.addItem(text,value)
  form.addRow(triple('الحالة','Statut','Status'),self.status);layout.addLayout(form);self.change_customer();self.table=QTableWidget(0,4);self.table.setHorizontalHeaderLabels([triple('الوصف','Description','Description'),triple('الفئة','Catégorie','Category'),triple('الكمية','Quantité','Quantity'),triple('السعر MAD','Prix MAD','Price MAD')]);layout.addWidget(self.table,1)
  row=QHBoxLayout();add=action_button(triple('إضافة بند','Ajouter ligne','Add line'));add.clicked.connect(self.add_line);row.addWidget(add);remove=action_button(triple('حذف بند','Retirer ligne','Remove line'));remove.clicked.connect(self.remove_line);row.addWidget(remove);layout.addLayout(row)
  fields=QHBoxLayout();self.discount=QLineEdit('0');self.tax=QLineEdit('0');self.legal={}
  for title,field in [(triple('خصم MAD','Remise MAD','Discount MAD'),self.discount),(triple('ضريبة يحددها المستخدم %','Taxe configurée %','User configured tax %'),self.tax)]:fields.addWidget(QLabel(title));fields.addWidget(field);field.textChanged.connect(self.update_total)
  for key in ('ICE','IF','RC'):
   field=QLineEdit();field.setPlaceholderText(key+' · '+triple('اختياري','Facultatif','Optional'));self.legal[key]=field;fields.addWidget(field)
  layout.addLayout(fields);self.total=QLabel();layout.addWidget(self.total);self.report=QComboBox();self.report.addItem(triple('دون تقرير مرتبط','Sans rapport associé','No associated report'),None)
  for r in store.reports():
   result=r.get('result');evidence=result.get('evidence','unknown') if isinstance(result,dict) else 'unknown';self.report.addItem(f'#{r["id"]} · {r["time"]} · {"SIMULATOR" if evidence=="simulator" else evidence}',{'id':r['id'],'evidence':evidence,'command':r['command']})
  layout.addWidget(self.report);self.feedback=QLabel();self.feedback.setWordWrap(True);layout.addWidget(self.feedback);actions=QHBoxLayout();save=action_button(triple('حفظ الفاتورة','Enregistrer facture','Save invoice'),role='primary');save.clicked.connect(self.save);actions.addWidget(save);history=action_button(triple('سجل الفواتير','Historique factures','Invoice history'));history.clicked.connect(lambda:invoice_history(window));actions.addWidget(history);layout.addLayout(actions);self.add_line()
 def change_customer(self,*args):
  self.vehicle.clear();row=self.customer.currentData()
  for v in vehicles(row or {}):self.vehicle.addItem(' · '.join(str(x) for x in v.values() if x),v)
 def add_line(self):
  i=self.table.rowCount();self.table.insertRow(i);description=QLineEdit();category=QComboBox()
  for text,value in [(triple('قطع','Pièces','Parts'),'parts'),(triple('عمل','Main-d’œuvre','Labor'),'labor'),(triple('خدمات','Services','Services'),'services')]:category.addItem(text,value)
  qty=QLineEdit('1');price=QLineEdit('0')
  for j,w in enumerate((description,category,qty,price)):self.table.setCellWidget(i,j,w)
  for w in (qty,price):w.textChanged.connect(self.update_total)
  self.update_total()
 def remove_line(self):
  if self.table.currentRow()>=0:self.table.removeRow(self.table.currentRow());self.update_total()
 def lines(self):return [{'description':self.table.cellWidget(i,0).text(),'category':self.table.cellWidget(i,1).currentData(),'qty':self.table.cellWidget(i,2).text(),'price':self.table.cellWidget(i,3).text()} for i in range(self.table.rowCount())]
 def update_total(self,*args):
  try:
   total=calculate(self.lines(),self.discount.text(),self.tax.text());self.total.setText('MAD · '+triple('المجموع','Total','Total')+' '+total['total']+' · '+triple('الضريبة','Taxe','Tax')+' '+total['tax'])
  except Exception as error:self.total.setText(str(error))
 def save(self):
  try:
   customer=self.customer.currentData()
   if not customer:raise ValueError(triple('اختر عميلاً','Choisir un client','Select a customer'))
   report=self.report.currentData()
   if report and report['evidence']=='simulator' and QMessageBox.question(self,'SIMULATOR',triple('هذا التقرير محاكاة وليس فحصاً فعلياً. ربطه بالفاتورة؟','Ce rapport est simulé, pas un diagnostic physique. L’associer ?','This is simulator evidence, not a physical scan. Associate it with this invoice?'))!=QMessageBox.Yes:return
   id=save_invoice(customer['id'],self.vehicle.currentData() or {},self.lines(),self.discount.text(),self.tax.text(),self.status.currentData(),{k:w.text() for k,w in self.legal.items()},report);self.feedback.setText(triple('حُفظت الفاتورة رقم ','Facture enregistrée n° ','Saved invoice #')+str(id))
  except Exception as error:self.feedback.setText(str(error))

def invoice_html(record):
 snapshot=json.loads(record['customer']);items=json.loads(record['lines']);legal=json.loads(record.get('legal_fields') or '{}');origin=json.loads(record.get('report_snapshot') or '{}');e=lambda v:escape(str(v));lines=''.join('<tr>'+''.join('<td>'+e(r.get(k,''))+'</td>' for k in ('description','category','qty','price'))+'</tr>' for r in items)
 return '<h1>GITM · '+triple('فاتورة','Facture','Invoice')+' #'+e(record['id'])+'</h1><p>'+e(record['date'])+' · '+e(record.get('status','unpaid'))+'</p><p>'+e(snapshot.get('name',''))+' · '+e(snapshot.get('phone',''))+'</p><p>'+e(json.loads(record.get('vehicle_snapshot') or '{}') or snapshot.get('vehicle',{}))+'</p><p>'+e(legal)+'</p><table border="1" cellspacing="0" cellpadding="7" width="100%"><tr><th>'+triple('الوصف','Description','Description')+'</th><th>'+triple('الفئة','Catégorie','Category')+'</th><th>'+triple('الكمية','Quantité','Quantity')+'</th><th>'+e(record['currency'])+'</th></tr>'+lines+'</table><p>'+triple('الخصم','Remise','Discount')+': '+e(record.get('discount','0'))+' '+e(record['currency'])+' · '+triple('الضريبة','Taxe','Tax')+': '+e(record.get('tax','0'))+' '+e(record['currency'])+' ('+e(record.get('tax_rate','0'))+'%)</p><h2>'+e(record['total'])+' '+e(record['currency'])+'</h2><p>'+('SIMULATOR · ' if origin.get('evidence')=='simulator' else '')+e(origin)+'</p>'

class InvoiceHistory(QWidget):
 def __init__(self,window):
  super().__init__();layout=QVBoxLayout(self);self.table=QTableWidget(0,5);configure_table(self.table);self.table.setHorizontalHeaderLabels(['ID',triple('التاريخ','Date','Date'),triple('العميل','Client','Customer'),triple('الحالة','Statut','Status'),triple('المجموع','Total','Total')]);layout.addWidget(self.table,1);self.preview=QTextBrowser();layout.addWidget(self.preview,1);actions=QHBoxLayout();self.buttons=[]
  for title,callback in [('PDF',lambda:self.output(True)),(triple('طباعة','Imprimer','Print'),lambda:self.output(False)),('JSON',self.export)]:b=action_button(title);b.clicked.connect(callback);actions.addWidget(b);self.buttons.append(b)
  self.status=QComboBox();self.status.addItem(triple('حالة قديمة غير مسجلة','Ancien statut non enregistré','Legacy status unrecorded'),'unknown')
  for text,value in [(triple('مسودة','Brouillon','Draft'),'draft'),(triple('غير مدفوعة','Impayée','Unpaid'),'unpaid'),(triple('مدفوعة','Payée','Paid'),'paid'),(triple('ملغاة','Annulée','Cancelled'),'cancelled')]:self.status.addItem(text,value)
  actions.addWidget(self.status);set_status=action_button(triple('تحديث الحالة','Modifier statut','Update status'));set_status.clicked.connect(self.update_status);actions.addWidget(set_status)
  layout.addLayout(actions);self.feedback=QLabel();layout.addWidget(self.feedback)
  with database() as c:c.row_factory=__import__('sqlite3').Row;self.rows=[dict(r) for r in c.execute('SELECT * FROM invoices ORDER BY id DESC LIMIT 1000')]
  self.table.setRowCount(len(self.rows))
  for i,r in enumerate(self.rows):
   for j,value in enumerate((r['id'],r['date'],json.loads(r['customer']).get('name','—'),r['status'],r['total']+' '+r['currency'])):self.table.setItem(i,j,QTableWidgetItem(str(value)))
  self.table.itemSelectionChanged.connect(self.select);self.select()
 def selected(self):
  index=self.table.currentRow();return self.rows[index] if 0<=index<len(self.rows) else None
 def select(self):
  record=self.selected()
  if record:self.status.setCurrentIndex(self.status.findData(record['status']))
  self.preview.setHtml(invoice_html(record) if record else triple('اختر فاتورة','Sélectionner une facture','Select an invoice'))
  for b in self.buttons:b.setEnabled(record is not None)
 def update_status(self):
  record=self.selected()
  if not record:return
  status=self.status.currentData()
  if status not in ('draft','unpaid','paid','cancelled'):return
  with database() as c:c.execute('UPDATE invoices SET status=? WHERE id=?',(status,record['id']))
  record['status']=status;self.table.item(self.table.currentRow(),3).setText(status);self.select()
 def output(self,pdf):
  record=self.selected()
  if not record:return
  try:
   printer=QPrinter()
   if pdf:
    path,_=QFileDialog.getSaveFileName(self,'PDF',f'invoice-{record["id"]}.pdf','PDF (*.pdf)')
    if not path:return
    printer.setOutputFormat(QPrinter.PdfFormat);printer.setOutputFileName(path)
   elif not QPrintDialog(printer,self).exec():return
   document=QTextDocument();document.setDefaultFont(self.font());document.setHtml(invoice_html(record));document.print_(printer)
   if pdf:self.feedback.setText(path)
  except Exception as error:self.feedback.setText(str(error))
 def export(self):
  record=self.selected()
  if not record:return
  path,_=QFileDialog.getSaveFileName(self,'JSON',f'invoice-{record["id"]}.json','JSON (*.json)')
  if path:
   try:private_json(path,record);self.feedback.setText(path)
   except Exception as error:self.feedback.setText(str(error))

def customers(window):
 layout=window.page(triple('العملاء والمركبات','Clients et véhicules','Customers and vehicles'));widget=Customers(window);layout.addWidget(widget);return widget

def invoices(window):
 layout=window.page(triple('فاتورة MAD','Facture MAD','MAD invoice'));widget=InvoiceEditor(window);layout.addWidget(widget);return widget

def invoice_history(window):
 layout=window.page(triple('سجل الفواتير','Historique des factures','Invoice history'));widget=InvoiceHistory(window);layout.addWidget(widget);return widget
