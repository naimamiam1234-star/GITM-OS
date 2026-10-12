"""Structured local DTC reference and explicitly sourced technical resources."""
from pathlib import Path
import json,re
from shiboken6 import isValid
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QTableWidget,QTableWidgetItem,QTextBrowser,QCheckBox,QFileDialog
from professional_components import triple as t,InfoCard,action_button,configure_table
from diagnostic_workspace import Worker
import automotive_data

class Reference(QWidget):
 def __init__(self,window):
  super().__init__();self.window=window;self.worker=None;root=QVBoxLayout(self);card=InfoCard(t('تعريف مرجعي، وليس تشخيصًا مؤكدًا','Référence, pas diagnostic confirmé','Reference definition, not a confirmed diagnosis'));root.addWidget(card)
  row=QHBoxLayout();self.code=QLineEdit();self.code.setPlaceholderText('P0401');self.code.setLayoutDirection(__import__('PySide6.QtCore',fromlist=['Qt']).Qt.LeftToRight);self.make=QLineEdit(window.vehicle.get('make',''));self.make.setPlaceholderText(t('المصنع اختياري','Fabricant facultatif','Manufacturer optional'));row.addWidget(self.code);row.addWidget(self.make);self.search=action_button(t('بحث محلي','Recherche locale','Local search'),'primary');self.search.clicked.connect(self.lookup);self.code.returnPressed.connect(self.lookup);row.addWidget(self.search);card.body.addLayout(row)
  self.table=QTableWidget(0,4);self.table.setHorizontalHeaderLabels([t('التعريف','Définition','Definition'),t('المصنع / ECU','Constructeur / ECU','Manufacturer / ECU'),t('المصدر','Source','Source'),t('التوافق','Application','Applicability')]);configure_table(self.table);root.addWidget(self.table,1);self.feedback=QLabel(t('أدخل رمز العطل للبحث في البيانات المحلية','Saisir un code pour chercher localement','Enter a DTC to search local records'));self.feedback.setWordWrap(True);root.addWidget(self.feedback)
 def lookup(self):
  code=self.code.text().strip().upper();make=self.make.text().strip()
  if not re.fullmatch('[PBCU][0-9A-F]{4}',code):self.feedback.setText(t('رمز غير صالح','Code invalide','Invalid DTC'));return
  if self.worker is not None or getattr(self.window,'_obd_worker',None) is not None or getattr(self.window,'task',None) is not None and self.window.task.isRunning():return
  self.worker=Worker(lambda c,p:automotive_data.dtc(code,make),self.window);worker=self.worker;self.window._obd_worker=worker;self.search.setEnabled(False);self.feedback.setText(t('بحث جارٍ','Recherche en cours','Searching'))
  worker.result.connect(lambda result:self.display(result) if isValid(self) and not worker.cancel.is_set() else None);worker.failure.connect(lambda error:self.feedback.setText(str(error)) if isValid(self) else None)
  def finished():
   if getattr(self.window,'_obd_worker',None) is worker:self.window._obd_worker=None
   if isValid(self):self.worker=None;self.search.setEnabled(True)
  worker.finished.connect(finished);worker.start()
 def display(self,result):
  defs=result.get('definitions',[]);self.table.setRowCount(len(defs))
  for i,d in enumerate(defs):
   for j,value in enumerate([d.get('definition') or d.get('description','—'),str(d.get('manufacturer',''))+' / '+str(d.get('ecu','')),str(d.get('source',''))+' · '+str(d.get('source_file','')),d.get('applicability','—')]):item=QTableWidgetItem(str(value));item.setToolTip(str(value));self.table.setItem(i,j,item)
  self.table.setColumnWidth(0,300);self.table.setColumnWidth(2,230);self.feedback.setText(t('تحقق من انطباق المرجع على السيارة والوحدة','Vérifier l’application au véhicule et ECU','Verify reference applicability to the vehicle and ECU') if defs else t('لا توجد تعريفات مطابقة','Aucune définition correspondante','No matching definitions'))
 def hideEvent(self,event):
  if self.worker:self.worker.cancel.set()
  super().hideEvent(event)

def show(window,kind='dtc'):
 l=window.page(t('المعرفة الفنية','Connaissances techniques','Technical knowledge'));widget=Reference(window);l.addWidget(widget);return widget
