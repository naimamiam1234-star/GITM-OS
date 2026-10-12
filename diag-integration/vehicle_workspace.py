"""Persistent manual identity; explicit consent is required for VIN lookup."""
import json,hashlib,datetime
from pathlib import Path
from PySide6.QtCore import QSize,Qt
from PySide6.QtGui import QPixmap,QIcon,QPainter,QColor
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QScrollArea,QLineEdit,QFormLayout,QCheckBox,QTextEdit,QLabel,QComboBox,QTabWidget,QFileDialog
import native,store,source_gateway
from professional_components import triple,action_button,InfoCard
from vci_workspace import Workspace as ConnectionWorkspace

def text(ar,fr,en):return triple(ar,fr,en)
class Choice(QComboBox):
 def __init__(self,value='',choices=()):
  super().__init__();self.setEditable(True);self.addItems(['']+list(choices));self.setText(value)
 def text(self):return self.currentText()
 def setText(self,value):self.setEditText(str(value))
 @property
 def textChanged(self):return self.currentTextChanged

class Workspace(QWidget):
 launch=ConnectionWorkspace.launch
 error=ConnectionWorkspace.error
 def __init__(self,window,logos=None):
  super().__init__();self.window=window;self.worker=None;self.actions=[];root=QVBoxLayout(self);self.tabs=QTabWidget();self.tabs.setMaximumHeight(520);root.addWidget(self.tabs,1);brands=QWidget();details=QWidget();self.tabs.addTab(brands,text('1 · الماركة','1 · Marque','1 · Make'));self.tabs.addTab(details,text('2 · السيارة والمحرك','2 · Véhicule et moteur','2 · Vehicle and engine'));brand_layout=QVBoxLayout(brands);detail_layout=QVBoxLayout(details);self.search=QLineEdit();self.search.setPlaceholderText(text('ابحث عن الماركة','Rechercher une marque','Search makes'));brand_layout.addWidget(self.search)
  self.favorites=set(store.cache('vehicle_favorites') or []);self.only_favorites=QCheckBox(text('المفضلة فقط','Favoris seulement','Favorites only'));brand_layout.addWidget(self.only_favorites)
  self.scroll=QScrollArea();self.scroll.setWidgetResizable(True);brand_layout.addWidget(self.scroll,1);container=QWidget();self.grid=QGridLayout(container);self.scroll.setWidget(container);self.buttons={}
  base=Path(native.__file__).parent
  if logos is None:
   try:logos=json.loads((base/'data/logos.json').read_text())
   except (OSError,ValueError):logos={}
  for name,data in logos.items():
   button=action_button(name);button.setObjectName('vehicleBrand');button.setIconSize(QSize(32,24));pix=QPixmap(str(base/str(data.get('path','')).lstrip('/')))
   if not pix.isNull():
    # Source brand marks are often black; a neutral tile stays readable in both themes.
    logo=pix.scaled(28,20,Qt.KeepAspectRatio,Qt.SmoothTransformation);tile=QPixmap(32,24);tile.fill(Qt.transparent);painter=QPainter(tile);painter.setRenderHint(QPainter.Antialiasing);painter.setPen(Qt.NoPen);painter.setBrush(QColor('#f4f6f8'));painter.drawRoundedRect(0,0,32,24,3,3);painter.drawPixmap((32-logo.width())//2,(24-logo.height())//2,logo);painter.end();button.setIcon(QIcon(tile))
   button.setCheckable(True);button.clicked.connect(lambda checked=False,n=name:self.fields['make'].setText(n));self.buttons[name]=button
  self.search.textChanged.connect(self.reflow);self.only_favorites.toggled.connect(self.reflow)
  self.fields={};row=QHBoxLayout();detail_layout.addLayout(row,1);identity=InfoCard(text('هوية السيارة','Identité véhicule','Vehicle identity'));row.addWidget(identity,3);identity.body.setAlignment(Qt.AlignTop);identity.setMaximumHeight(380);form=QFormLayout();identity.body.addLayout(form);image_card=InfoCard(text('صورة السيارة المختارة','Photo du véhicule','Selected vehicle photo'));row.addWidget(image_card,2);image_card.setMaximumHeight(380);self.photo=QLabel();self.photo.setAlignment(Qt.AlignCenter);self.photo.setMinimumSize(160,130);self.photo.setWordWrap(True);image_card.body.addWidget(self.photo,1);self.photo_path='';self.photo_identity=None;attach=action_button(text('إضافة صورة السيارة','Ajouter une photo','Attach vehicle photo'));attach.clicked.connect(self.attach_photo);image_card.body.addWidget(attach);self.summary=QLabel();self.summary.setWordWrap(True);image_card.body.addWidget(self.summary)
  saved=dict(getattr(window,'vehicle',{}) or store.cache('vehicle_selection') or {})
  if saved and not getattr(window,'vehicle',{}):window.vehicle=dict(saved)
  for key,label in [('make',text('الماركة','Marque','Make')),('model',text('الموديل','Modèle','Model')),('year',text('السنة','Année','Year')),('engine',text('المحرك','Moteur','Engine')),('vin','VIN'),('fuel',text('نوع الطاقة / الوقود','Énergie / carburant','Powertrain / fuel'))]:
   value=str(saved.get(key,'') or '');choices=[str(y) for y in range(datetime.date.today().year+1,1979,-1)] if key=='year' else ['Gasoline','Diesel','Electric','Hybrid','Plug-in hybrid','LPG','CNG','Ethanol','Hydrogen','Other'] if key=='fuel' else [];entry=Choice(value,choices) if key in ('model','year','engine','fuel') else QLineEdit(value);entry.setObjectName('vehicle_'+key);form.addRow(label,entry);self.fields[key]=entry
  self.photo_path=saved.get('photo_path','');self.photo_identity=saved.get('photo_identity')
  for field in self.fields.values():field.textChanged.connect(self.refresh_state)
  self.refresh_state()
  self.consent=QCheckBox(text('أوافق على إرسال VIN إلى NHTSA','Autoriser l’envoi du VIN à NHTSA','Allow sending VIN to NHTSA'));detail_layout.addWidget(self.consent)
  actions=QHBoxLayout();root.addLayout(actions)
  for label,fn in [(text('اعتماد الاختيار','Enregistrer sélection','Save selection'),self.save_selection),(text('تبديل المفضلة','Basculer favori','Toggle favorite'),self.favorite),(text('بحث VIN','Rechercher VIN','Look up VIN'),self.lookup)]:
   b=action_button(label);b.clicked.connect(fn);actions.addWidget(b);self.actions.append(b)
  self.vin_candidate=None;self.vin_apply=action_button(text('اعتماد بيانات VIN المعروضة','Appliquer les données VIN','Apply displayed VIN identity'));self.vin_apply.setEnabled(False);self.vin_apply.hide();self.vin_apply.clicked.connect(self.apply_vin);detail_layout.addWidget(self.vin_apply)
  self.status=QLabel();root.addWidget(self.status);scope=QLabel(text('اختيار يدوي؛ دعم وحدات OEM غير مثبت. OBD عام حسب المحول والسيارة.','Sélection manuelle ; support OEM non établi. OBD générique selon véhicule et adaptateur.','Manual identity; OEM module support is not established. Generic OBD depends on vehicle and adapter.'));scope.setWordWrap(True);root.addWidget(scope)
  self.log=QTextEdit();self.log.setReadOnly(True);self.log.setMaximumHeight(70);self.log.hide();root.addWidget(self.log);self.reflow()
 def refresh_state(self):
  if len(self.fields)<6:return
  selected=self.fields['make'].text().strip().casefold()
  for name,button in self.buttons.items():button.setChecked(name.casefold()==selected)
  self.summary.setText(' · '.join(self.fields[k].text() or '—' for k in ('make','model','year','engine','fuel')))
  self.photo.clear()
  if self.photo_path and self.photo_identity==self.identity():
   pix=QPixmap(self.photo_path)
   if not pix.isNull():self.photo.setPixmap(pix.scaled(280,180,Qt.KeepAspectRatio,Qt.SmoothTransformation));return
  self.photo.setText(text('أضف صورة هذه السيارة؛ لا توجد صورة مطابقة','Ajouter la photo de ce véhicule ; aucune correspondance','Attach this vehicle photo; no matching image'))
 @staticmethod
 def columns_for(width):return 5 if width>=1600 else 4 if width>=1150 else 3 if width>=800 else 2
 def columns(self):return self.columns_for(self.window.width() if self.parentWidget() is not None else self.width())
 def reflow(self,*args):
  while self.grid.count():self.grid.takeAt(0)
  selected=[(n,b) for n,b in self.buttons.items() if self.search.text().casefold() in n.casefold() and (not self.only_favorites.isChecked() or n in self.favorites)]
  for b in self.buttons.values():b.hide()
  for i,(name,b) in enumerate(selected):self.grid.addWidget(b,i//self.columns(),i%self.columns());b.show()
 def resizeEvent(self,event):super().resizeEvent(event);self.reflow()
 def identity(self):
  result={k:self.fields[k].text().strip() for k in ('make','model','year','engine','vin','fuel')};result['vin']=result['vin'].upper();return result
 def attach_photo(self):
  filename,_=QFileDialog.getOpenFileName(self,text('صورة السيارة','Photo du véhicule','Vehicle photo'),'','Images (*.png *.jpg *.jpeg *.webp)')
  if not filename:return
  path=Path(filename)
  if path.stat().st_size>20*1024*1024:self.error(text('الصورة أكبر من 20MB','Image supérieure à 20MB','Image exceeds 20MB'));return
  pix=QPixmap(filename)
  if pix.isNull():self.error(text('صورة غير صالحة','Image invalide','Invalid image'));return
  destination=store.BASE/'vehicle-photos';destination.mkdir(parents=True,exist_ok=True);target=destination/(hashlib.sha256(path.read_bytes()).hexdigest()+'.png');pix.scaled(1600,1200,Qt.KeepAspectRatio,Qt.SmoothTransformation).save(str(target));self.photo_path=str(target);self.photo_identity=self.identity();self.refresh_state()
 def display_vin(self,vin,result):
  if self.fields['vin'].text().strip().upper()!=vin:return
  self.vin_candidate=(vin,result);self.vin_apply.setEnabled(True);self.vin_apply.show();self.log.show();self.log.setPlainText(json.dumps(result,ensure_ascii=False,indent=2));self.tabs.setCurrentIndex(1)
 def apply_vin(self):
  if not self.vin_candidate:return
  vin,result=self.vin_candidate
  if self.fields['vin'].text().strip().upper()!=vin:return
  row=result.get('vehicle',{})
  for field,key in [('make','Make'),('model','Model'),('year','ModelYear'),('engine','EngineModel'),('fuel','FuelTypePrimary')]:
   value=str(row.get(key,'') or '').strip()
   if value:self.fields[field].setText(value)
  self.vin_apply.setEnabled(False)
 def save_selection(self):
  vehicle={k:v.text().strip() for k,v in self.fields.items()};vehicle['vin']=vehicle['vin'].upper();vehicle['source']='manual';vehicle['coverage']='Generic emissions OBD; OEM support not established';
  if self.photo_path and self.photo_identity==self.identity():vehicle.update(photo_path=self.photo_path,photo_identity=self.photo_identity)
  self.window.vehicle=vehicle;store.cache('vehicle_selection',vehicle);self.log.setPlainText(json.dumps(vehicle,ensure_ascii=False,indent=2))
  if hasattr(self.window,'refresh'):self.window.refresh()
 def favorite(self):
  make=self.fields['make'].text().strip()
  if not make:return
  if make in self.favorites:self.favorites.remove(make)
  else:self.favorites.add(make)
  store.cache('vehicle_favorites',sorted(self.favorites));self.reflow()
 def lookup(self):
  vin=self.fields['vin'].text().strip().upper();consent=self.consent.isChecked()
  if not consent:self.error(text('الموافقة مطلوبة لإرسال VIN','Consentement requis pour envoyer le VIN','Consent is required to send VIN'));return
  self.launch(lambda c,p:source_gateway.decode_vin(vin,consent),lambda result:self.display_vin(vin,result))
 def hideEvent(self,event):
  if self.worker:self.worker.cancel.set()
  super().hideEvent(event)
def show(window):
 layout=window.page(text('اختيار السيارة','Sélection véhicule','Vehicle selection'));page=Workspace(window);layout.addWidget(page);return page
