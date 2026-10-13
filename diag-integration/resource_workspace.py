"""Offline source catalog and general OBD connector reference, without ECU traffic."""
import json
from pathlib import Path
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QTableWidget,QTableWidgetItem,QTextEdit,QSplitter,QFileDialog
from vci_workspace import Workspace as ConnectionWorkspace
from professional_components import triple,InfoCard,MetricCard,action_button,configure_table

def t(ar,fr,en):return triple(ar,fr,en)
def flag(value):
 return t('نعم','Oui','Yes') if value is True else t('لا','Non','No') if value is False else '—'
def searchable(row):
 return ' '.join(str(row.get(key,'')) for key in ('name','status','redistribution','license','id','categories','makes','protocols','coverage')).casefold()
def catalog_extension():
 path=Path(__file__).parent/'source_catalog_extension.json'
 try:
  rows=json.loads(path.read_text(encoding='utf-8'))
  if not isinstance(rows,list) or any(not isinstance(row,dict) for row in rows):raise ValueError('Invalid source extension')
  return rows
 except (OSError,ValueError):return []
def load_sources(path=None):
 if path is None:
  import native
  root=getattr(native,'ROOT',Path(native.__file__).parent);path=Path(root)/'sources.json'
 try:
  path=Path(path)
  if path.stat().st_size>2*1024*1024:raise ValueError('Source catalog exceeds local read limit')
  rows=json.loads(path.read_text(encoding='utf-8'))
  if not isinstance(rows,list) or any(not isinstance(row,dict) for row in rows):raise ValueError('Source catalog must be a list of records')
  if path.name=='sources.json':
   known={row.get('url','').rstrip('/').casefold() for row in rows}
   for extra in catalog_extension():
    existing=next((row for row in rows if row.get('url','').rstrip('/').casefold()==extra['url'].rstrip('/').casefold()),None)
    if existing is not None:
     for key in ('categories','makes','protocols','coverage','reviewed_utc'):existing[key]=extra[key]
    else:rows.append(extra)
  return rows,''
 except (OSError,ValueError,TypeError) as exc:return [],str(exc)

def load_audit(path=None):
 if path is None:path=Path(__file__).parent/'source_audit.json'
 try:
  path=Path(path)
  if path.stat().st_size>2*1024*1024:raise ValueError('Audit exceeds local read limit')
  audit=json.loads(path.read_text(encoding='utf-8'))
  if not isinstance(audit,dict) or any(not isinstance(audit.get(key,[]),list) for key in ('bundled_libraries','tested_integrations')):raise ValueError('Invalid audit schema')
  return audit,''
 except (OSError,ValueError,TypeError) as exc:return {},str(exc)

class SourcesWorkspace(QWidget):
 launch=ConnectionWorkspace.launch
 error=ConnectionWorkspace.error
 def refresh_state(self):pass
 def __init__(self,window,rows=None,audit=None):
  super().__init__();self.window=window;self.worker=None;self.actions=[];self.records,self.load_error=load_sources() if rows is None else (list(rows),'');self.filtered=[];root=QVBoxLayout(self)
  summary=QHBoxLayout();root.addLayout(summary);count=MetricCard(t('روابط مرجعية','Liens de référence','Reference links'),len(self.records));summary.addWidget(count);self.verified_count=MetricCard(t('دمج مصادر موثق','Intégrations du catalogue vérifiées','Catalog integrations verified'),sum(row.get('integration_verified') is True for row in self.records));summary.addWidget(self.verified_count)
  self.audit,self.audit_error=load_audit() if audit is None else (audit,'')
  self.license_count=MetricCard(t('تراخيص مكتبات مفحوصة','Licences de bibliothèques inspectées','Bundled licenses inspected'),sum(row.get('license_inspected') is True for row in self.audit.get('bundled_libraries',[])));summary.addWidget(self.license_count)
  self.software_count=MetricCard(t('فحوص برمجية ناجحة','Contrôles logiciels réussis','Software checks passed'),sum(row.get('tested') is True for row in self.audit.get('tested_integrations',[])));summary.addWidget(self.software_count)
  self.audit_scope=QLabel(t('فحص البرنامج: تحميل تبعية ODX فقط؛ ليس اختبار سيارة. التراخيص تخص المكتبات، وليس بيانات المصنع.','Contrôle logiciel : chargement de la dépendance ODX seulement ; aucun test véhicule. Licences des bibliothèques, pas des données constructeur.','Software check: ODX dependency loading only; no vehicle test. Licenses cover libraries, not manufacturer data.')+(' '+self.audit_error if self.audit_error else ''));self.audit_scope.setWordWrap(True);root.addWidget(self.audit_scope)
  scope=QLabel(t('فهرس محلي. الروابط ووجود الملفات لا يثبتان دعم السيارة أو حق إعادة التوزيع.','Catalogue local. Liens et fichiers ne prouvent ni couverture véhicule ni droits de redistribution.','Local catalog. Links and bundled files do not establish vehicle coverage or redistribution rights.'));scope.setWordWrap(True);root.addWidget(scope)
  self.search=QLineEdit();self.search.setPlaceholderText(t('ابحث في المصادر','Rechercher les sources','Search sources'));root.addWidget(self.search);self.search.textChanged.connect(self.refresh)
  split=QSplitter();root.addWidget(split,1);self.table=QTableWidget(0,4);self.table.setHorizontalHeaderLabels([t('مصدر','Source','Source'),t('دمج موثق','Vérifié','Verified'),t('إعادة توزيع','Redistribution','Redistribution'),t('الحالة','État','Status')]);configure_table(self.table);self.table.setColumnWidth(0,165);self.table.setColumnWidth(1,85);self.table.setColumnWidth(2,150);split.addWidget(self.table)
  card=InfoCard(t('تفاصيل المصدر','Détails de la source','Source details'));split.addWidget(card);self.details=QTextEdit();self.details.setReadOnly(True);card.body.addWidget(self.details);self.open_button=action_button(t('فتح رابط المصدر','Ouvrir le lien','Open source link'));self.open_button.clicked.connect(self.open_selected);card.body.addWidget(self.open_button);split.setStretchFactor(0,3);split.setStretchFactor(1,2)
  self.empty=QLabel();self.empty.setWordWrap(True);root.addWidget(self.empty)
  bar=QHBoxLayout();root.addLayout(bar)
  for label,callback in [(t('استيراد مرجع تقني JSON','Importer une référence JSON','Import technical evidence JSON'),self.import_evidence),(t('بحث استدعاءات السيارة','Rechercher les rappels','Look up vehicle recalls'),self.recalls)]:
   button=action_button(label);button.clicked.connect(callback);bar.addWidget(button);self.actions.append(button)
  transfer=QLabel(t('بحث الاستدعاءات يرسل الماركة والموديل والسنة إلى NHTSA عند الضغط فقط.','La recherche de rappels envoie marque, modèle et année à NHTSA uniquement au clic.','Recall lookup sends make, model and year to NHTSA only when clicked.'));transfer.setWordWrap(True);root.addWidget(transfer)
  files=action_button(t('مكتبة الملفات والمصادر المدمجة','Bibliothèque locale intégrée','Bundled files and source library'));files.clicked.connect(lambda:__import__('resource_library').show(window));bar.addWidget(files)
  self.status=QLabel();root.addWidget(self.status);self.log=QTextEdit();self.log.setReadOnly(True);self.log.setMaximumHeight(90);root.addWidget(self.log);self.table.itemSelectionChanged.connect(self.show_selected);self.refresh()
 def selected(self):
  row=self.table.currentRow();return self.filtered[row] if 0<=row<len(self.filtered) and self.table.selectedItems() else None
 def refresh(self,*args):
  query=self.search.text().casefold();self.filtered=[row for row in self.records if query in searchable(row)];self.table.blockSignals(True);self.table.setRowCount(len(self.filtered))
  for i,row in enumerate(self.filtered):
   for j,value in enumerate((row.get('name','—'),flag(row.get('integration_verified')),row.get('redistribution','—'),row.get('status','—'))):
    item=QTableWidgetItem(str(value));item.setToolTip(str(value));self.table.setItem(i,j,item)
  self.table.blockSignals(False)
  if self.filtered:self.table.selectRow(0)
  self.empty.setVisible(not self.filtered);self.empty.setText((t('تعذر قراءة الفهرس: ','Lecture du catalogue impossible : ','Cannot read local catalog: ')+self.load_error) if self.load_error else t('لا توجد نتائج؛ غيّر البحث أو أضف مراجع محلية مرخصة.','Aucun résultat ; modifier la recherche ou ajouter des références locales autorisées.','No sources match. Adjust the search or add licensed local references.'));self.show_selected()
 def show_selected(self):
  row=self.selected();self.open_button.setEnabled(bool(row and self.valid_url(row.get('url'))))
  if row is None:self.details.clear();return
  lines=[]
  for label,value in [(t('الاسم','Nom','Name'),row.get('name')),(t('الحالة','État','Status'),row.get('status')),(t('الترخيص','Licence','License'),row.get('license')),(t('إعادة التوزيع','Redistribution','Redistribution'),row.get('redistribution')),(t('دمج موثق','Intégration vérifiée','Integration verified'),flag(row.get('integration_verified'))),(t('المعرف','Identifiant','Record ID'),row.get('id')),(t('ملفات محلية','Fichiers locaux','Local data path'),row.get('data_path')),(t('المجالات','Domaines','Categories'),row.get('categories')),(t('الماركات','Marques','Makes'),row.get('makes')),(t('البروتوكولات','Protocoles','Protocols'),row.get('protocols')),(t('التغطية','Couverture','Coverage'),row.get('coverage')),(t('الرابط','Lien','URL'),row.get('url'))]:lines.append(str(label)+': '+str(value if value not in (None,'') else '—'))
  self.details.setPlainText('\n\n'.join(lines))
 def import_evidence(self):
  path,_=QFileDialog.getOpenFileName(self,t('استيراد مرجع تقني مع مصدر وترخيص','Importer une référence avec source et licence','Import evidence with source and license'),'', 'JSON (*.json)')
  if not path:return
  def operation(cancel,progress,filename=str(path)):
   from knowledge import import_document
   source=Path(filename)
   if source.stat().st_size>2*1024*1024:raise ValueError('Evidence file exceeds local read limit')
   return import_document(json.loads(source.read_text(encoding='utf-8')))
  self.launch(operation,lambda result:self.log.setPlainText(json.dumps(result,ensure_ascii=False,indent=2)))
 def recalls(self):
  import source_gateway
  vehicle=dict(getattr(self.window,'vehicle',{}));args=(vehicle.get('make',''),vehicle.get('model',''),vehicle.get('year',''))
  if not all(args):self.error(t('اختر الماركة والموديل والسنة أولاً','Sélectionner marque, modèle et année','Select make, model and year first'));return
  self.launch(lambda cancel,progress:source_gateway.recalls(*args),lambda result:self.log.setPlainText(json.dumps(result,ensure_ascii=False,indent=2)))
 def hideEvent(self,event):
  if self.worker:self.worker.cancel.set()
  super().hideEvent(event)
 @staticmethod
 def valid_url(value):
  url=QUrl(str(value or ''));return url.isValid() and url.scheme() in ('https','http') and bool(url.host()) and not url.userInfo()
 def open_selected(self):
  row=self.selected()
  if row and self.valid_url(row.get('url')):QDesktopServices.openUrl(QUrl(row['url']))

class WiringWorkspace(QWidget):
 def __init__(self,window):
  super().__init__();self.window=window;root=QVBoxLayout(self);card=InfoCard(t('موصل OBD ذو 16 طرفاً','Connecteur OBD à 16 broches','16-pin OBD connector'));root.addWidget(card)
  self.scope=QLabel(t('مرجع عام فقط؛ لا توجد قراءة كهربائية أو تحقق من السيارة أو المحول. أرقام الأطراف بحسب الموصل؛ تحقق من وثائق المصنع قبل التوصيل.','Référence générale ; aucune mesure électrique ni validation véhicule/adaptateur. Vérifier la numérotation et la documentation constructeur avant connexion.','General reference only; no electrical measurements or vehicle/adapter verification. Confirm connector pin numbering and manufacturer documentation before connecting.'));self.scope.setWordWrap(True);card.body.addWidget(self.scope)
  self.table=QTableWidget(16,3);self.table.setHorizontalHeaderLabels([t('طرف','Broche','Pin'),t('وظيفة مرجعية','Fonction de référence','Reference assignment'),t('الحدود','Limites','Limitations')]);configure_table(self.table);self.table.setColumnWidth(0,65);self.table.setColumnWidth(1,210);root.addWidget(self.table,1)
  assigned={4:t('أرضي الهيكل','Masse châssis','Chassis ground'),5:t('أرضي الإشارة','Masse signal','Signal ground'),6:'CAN H',7:'K-Line',14:'CAN L',16:t('تغذية البطارية (+12 V اسمي)','Alimentation batterie (+12 V nominal)','Battery supply (nominal +12 V)')}
  unspecified=t('حسب البروتوكول والمصنع','Selon protocole et constructeur','Protocol / manufacturer dependent');limitation=t('مرجع؛ الاستخدام ووجود الطرف غير مثبتين','Référence ; présence et utilisation non vérifiées','Reference; pin presence and use are not verified')
  for pin in range(1,17):
   for col,value in enumerate((pin,assigned.get(pin,unspecified),limitation)):self.table.setItem(pin-1,col,QTableWidgetItem(str(value)))
  note=QLabel(t('الأطراف 6/14 لا تثبت دعم CAN FD أو جميع وحدات ECU. هذا المرجع لا ينفذ أوامر أو تشغيل محركات.','Les broches 6/14 ne prouvent ni CAN FD ni couverture de tous les calculateurs. Aucune commande ou activation moteur.','Pins 6/14 do not establish CAN FD or full ECU coverage. This reference issues no commands or motor activations.'));note.setWordWrap(True);root.addWidget(note)

def show(window,kind='sources'):
 if kind not in ('sources','wiring'):raise ValueError('Unknown resource page')
 layout=window.page(t('المصادر','Sources','Sources') if kind=='sources' else t('مرجع توصيل VCI','Référence VCI','VCI connector reference'));page=SourcesWorkspace(window) if kind=='sources' else WiringWorkspace(window);layout.addWidget(page);return page
