"""Persistent manual identity; explicit consent is required for VIN lookup."""
import json
from pathlib import Path
from PySide6.QtCore import QSize,Qt
from PySide6.QtGui import QPixmap,QIcon
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QScrollArea,QLineEdit,QFormLayout,QCheckBox,QTextEdit,QLabel
import native,store,source_gateway
from professional_components import triple,action_button
from vci_workspace import Workspace as ConnectionWorkspace

def text(ar,fr,en):return triple(ar,fr,en)
class Workspace(QWidget):
 launch=ConnectionWorkspace.launch
 error=ConnectionWorkspace.error
 def __init__(self,window,logos=None):
  super().__init__();self.window=window;self.worker=None;self.actions=[];root=QVBoxLayout(self);self.search=QLineEdit();self.search.setPlaceholderText(text('ابحث عن الماركة','Rechercher une marque','Search makes'));root.addWidget(self.search)
  self.favorites=set(store.cache('vehicle_favorites') or []);self.only_favorites=QCheckBox(text('المفضلة فقط','Favoris seulement','Favorites only'));root.addWidget(self.only_favorites)
  self.scroll=QScrollArea();self.scroll.setWidgetResizable(True);root.addWidget(self.scroll,1);container=QWidget();self.grid=QGridLayout(container);self.scroll.setWidget(container);self.buttons={}
  base=Path(native.__file__).parent
  if logos is None:
   try:logos=json.loads((base/'data/logos.json').read_text())
   except (OSError,ValueError):logos={}
  for name,data in logos.items():
   button=action_button(name);button.setMinimumHeight(80);button.setIconSize(QSize(64,48));pix=QPixmap(str(base/str(data.get('path','')).lstrip('/')))
   if not pix.isNull():button.setIcon(QIcon(pix.scaled(64,48,Qt.KeepAspectRatio,Qt.SmoothTransformation)))
   button.clicked.connect(lambda checked=False,n=name:self.fields['make'].setText(n));self.buttons[name]=button
  self.search.textChanged.connect(self.reflow);self.only_favorites.toggled.connect(self.reflow)
  self.fields={};form=QFormLayout();root.addLayout(form)
  saved=dict(getattr(window,'vehicle',{}) or store.cache('vehicle_selection') or {})
  if saved and not getattr(window,'vehicle',{}):window.vehicle=dict(saved)
  for key,label in [('make',text('الماركة','Marque','Make')),('model',text('الموديل','Modèle','Model')),('year',text('السنة','Année','Year')),('engine',text('المحرك','Moteur','Engine')),('vin','VIN')]:
   entry=QLineEdit(str(saved.get(key,'') or ''));entry.setObjectName('vehicle_'+key);form.addRow(label,entry);self.fields[key]=entry
  self.consent=QCheckBox(text('أوافق على إرسال VIN إلى NHTSA','Autoriser l’envoi du VIN à NHTSA','Allow sending VIN to NHTSA'));root.addWidget(self.consent)
  actions=QHBoxLayout();root.addLayout(actions)
  for label,fn in [(text('اعتماد الاختيار','Enregistrer sélection','Save selection'),self.save_selection),(text('تبديل المفضلة','Basculer favori','Toggle favorite'),self.favorite),(text('بحث VIN','Rechercher VIN','Look up VIN'),self.lookup)]:
   b=action_button(label);b.clicked.connect(fn);actions.addWidget(b);self.actions.append(b)
  self.status=QLabel();root.addWidget(self.status);scope=QLabel(text('اختيار يدوي؛ دعم وحدات OEM غير مثبت. OBD عام حسب المحول والسيارة.','Sélection manuelle ; support OEM non établi. OBD générique selon véhicule et adaptateur.','Manual identity; OEM module support is not established. Generic OBD depends on vehicle and adapter.'));scope.setWordWrap(True);root.addWidget(scope)
  self.log=QTextEdit();self.log.setReadOnly(True);self.log.setMaximumHeight(100);root.addWidget(self.log);self.reflow()
 def refresh_state(self):pass
 @staticmethod
 def columns_for(width):return 5 if width>=1600 else 4 if width>=1150 else 3 if width>=800 else 2
 def columns(self):return self.columns_for(self.window.width() if self.parentWidget() is not None else self.width())
 def reflow(self,*args):
  while self.grid.count():self.grid.takeAt(0)
  selected=[(n,b) for n,b in self.buttons.items() if self.search.text().casefold() in n.casefold() and (not self.only_favorites.isChecked() or n in self.favorites)]
  for b in self.buttons.values():b.hide()
  for i,(name,b) in enumerate(selected):self.grid.addWidget(b,i//self.columns(),i%self.columns());b.show()
 def resizeEvent(self,event):super().resizeEvent(event);self.reflow()
 def save_selection(self):
  vehicle={k:v.text().strip() for k,v in self.fields.items()};vehicle['vin']=vehicle['vin'].upper();vehicle['source']='manual';vehicle['coverage']='Generic emissions OBD; OEM support not established';self.window.vehicle=vehicle;store.cache('vehicle_selection',vehicle);self.log.setPlainText(json.dumps(vehicle,ensure_ascii=False,indent=2))
  if hasattr(self.window,'refresh'):self.window.refresh()
 def favorite(self):
  make=self.fields['make'].text().strip()
  if not make:return
  if make in self.favorites:self.favorites.remove(make)
  else:self.favorites.add(make)
  store.cache('vehicle_favorites',sorted(self.favorites));self.reflow()
 def lookup(self):
  vin=self.fields['vin'].text().strip();consent=self.consent.isChecked()
  if not consent:self.error(text('الموافقة مطلوبة لإرسال VIN','Consentement requis pour envoyer le VIN','Consent is required to send VIN'));return
  self.launch(lambda c,p:source_gateway.decode_vin(vin,consent),lambda result:self.log.setPlainText(json.dumps(result,ensure_ascii=False,indent=2)))
 def hideEvent(self,event):
  if self.worker:self.worker.cancel.set()
  super().hideEvent(event)
def show(window):
 layout=window.page(text('اختيار السيارة','Sélection véhicule','Vehicle selection'));page=Workspace(window);layout.addWidget(page);return page
