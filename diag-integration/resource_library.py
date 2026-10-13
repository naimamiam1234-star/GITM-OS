"""Installed source/data library. Availability is separate from vehicle support."""
import json,os
from pathlib import Path
from PySide6.QtCore import QUrl,Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QTableWidget,QTableWidgetItem,QTextBrowser,QSplitter
from professional_components import triple as t,MetricCard,action_button,configure_table
ROOT=Path(os.environ.get('GITM_RESOURCE_ROOT','/opt/gitm/resources'))
PORTAL='https://gitm-branding-preview.naimamiam1234.workers.dev'
def catalog(root=None):
 root=(root or ROOT).resolve();rows=[]
 for path in sorted(root.glob('catalog*.json')):
  try:
   if path.stat().st_size>4*1024*1024:continue
   value=json.loads(path.read_text(encoding='utf-8'))
   if isinstance(value,list):rows.extend(value)
  except (OSError,ValueError):continue
 output=[]
 for row in rows:
  if not isinstance(row,dict):continue
  path=(root/str(row.get('path',''))).resolve();valid=path.is_relative_to(root) and path.suffix.lower() in ('.zip','.json','.md','.txt','.pdf')
  output.append(dict(row,present=valid and path.is_file(),local_path=path if valid else None))
 return output
class Library(QWidget):
 def __init__(self,window):
  super().__init__();self.window=window;self.rows=[];self.filtered=[];layout=QVBoxLayout(self);layout.setSpacing(12)
  row=QHBoxLayout();self.installed=MetricCard(t('ملفات مثبتة','Fichiers installés','Installed files'));self.archives=MetricCard(t('أرشيفات مصدر','Archives source','Source archives'));row.addWidget(self.installed);row.addWidget(self.archives);layout.addLayout(row)
  notice=QLabel(t('ملفات المصدر والتعريفات مراجع محلية؛ لا تعني اعتماد وظائف على سيارة فعلية. تبقى البرمجة والاختبارات التنفيذية مرتبطة بتوافق ECU والمحول.','Sources et définitions locales ne valident pas les fonctions sur véhicule réel. Compatibilité ECU et VCI requise.','Local sources and definitions do not validate real-vehicle functions. ECU and adapter compatibility remain required.'));notice.setWordWrap(True);layout.addWidget(notice)
  self.search=QLineEdit();self.search.setPlaceholderText(t('ابحث بالماركة، الموديل، المكتبة أو نوع المورد','Marque, modèle, bibliothèque ou type','Search make, model, library or resource type'));self.search.textChanged.connect(self.filter);layout.addWidget(self.search)
  split=QSplitter();layout.addWidget(split,1);self.table=QTableWidget(0,3);self.table.setHorizontalHeaderLabels([t('المورد','Ressource','Resource'),t('الفئة','Catégorie','Category'),t('التوفر','Disponibilité','Availability')]);configure_table(self.table);split.addWidget(self.table);self.details=QTextBrowser();self.details.setOpenExternalLinks(False);split.addWidget(self.details);split.setStretchFactor(0,3);split.setStretchFactor(1,2);self.table.itemSelectionChanged.connect(self.describe)
  actions=QHBoxLayout();self.open=action_button(t('استعراض الملف المحلي','Ouvrir le fichier local','Open local file'),'primary');self.open.clicked.connect(self.open_local);actions.addWidget(self.open)
  self.source=action_button(t('المصدر الأصلي','Source originale','Original source'));self.source.clicked.connect(self.open_source);actions.addWidget(self.source)
  portal=action_button(t('مركز GITM على الإنترنت','Portail GITM','GITM online portal'));portal.clicked.connect(lambda:QDesktopServices.openUrl(QUrl(PORTAL)));actions.addWidget(portal);layout.addLayout(actions)
  self.status=QLabel();self.status.setWordWrap(True);layout.addWidget(self.status);self.reload()
 def reload(self):
  self.rows=catalog();self.installed.set_value(sum(bool(r['present']) for r in self.rows));self.archives.set_value(sum(r['present'] and str(r.get('path','')).endswith('.zip') for r in self.rows));self.filter()
 def filter(self,*args):
  query=self.search.text().casefold();self.filtered=[r for r in self.rows if query in json.dumps({k:v for k,v in r.items() if k!='local_path'},ensure_ascii=False).casefold()];self.table.setRowCount(len(self.filtered))
  for i,r in enumerate(self.filtered):
   for j,value in enumerate((r.get('name','—'),r.get('category','—'),t('مثبت محليًا','Installé','Installed') if r['present'] else t('مرجع أو حزمة غير مثبتة','Référence ou paquet absent','Reference or package not installed'))):self.table.setItem(i,j,QTableWidgetItem(str(value)))
  if self.filtered:self.table.selectRow(0)
  self.status.setText('' if self.filtered else t('لا توجد نتائج. ثبّت حزم الموارد أو غيّر البحث.','Aucun résultat. Installer les ressources ou modifier la recherche.','No results. Install resource packs or change the search.'));self.describe()
 def selected(self):
  i=self.table.currentRow();return self.filtered[i] if 0<=i<len(self.filtered) else None
 def describe(self):
  r=self.selected();self.open.setEnabled(bool(r and r['present']));self.source.setEnabled(bool(r and str(r.get('source_url','')).startswith('https://')))
  self.details.setPlainText(json.dumps({k:v for k,v in (r or {}).items() if k!='local_path'},ensure_ascii=False,indent=2))
 def open_local(self):
  r=self.selected()
  if r and r['present']:self.status.setText('' if QDesktopServices.openUrl(QUrl.fromLocalFile(str(r['local_path']))) else t('تعذر فتح الملف','Ouverture impossible','Could not open file'))
 def open_source(self):
  r=self.selected()
  if r and str(r.get('source_url','')).startswith('https://'):QDesktopServices.openUrl(QUrl(r['source_url']))
def show(window):
 if hasattr(window,'resource_library'):
  window.pages.setCurrentWidget(window.resource_library_page);window.resource_library.reload();return window.resource_library
 layout=window.page(t('مكتبة الملفات والمصادر','Bibliothèque locale','Local files and sources'));widget=Library(window);layout.addWidget(widget);window.resource_library=widget;window.resource_library_page=window.pages.currentWidget();return widget
