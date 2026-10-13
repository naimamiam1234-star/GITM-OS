"""Persistent manual identity; explicit consent is required for VIN lookup."""
import json,hashlib,datetime
from pathlib import Path
from PySide6.QtCore import QSize,Qt
from PySide6.QtGui import QPixmap,QIcon,QPainter,QColor,QFontMetrics
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QScrollArea,QLineEdit,QFormLayout,QCheckBox,QTextEdit,QLabel,QComboBox,QTabWidget,QFileDialog,QStackedWidget,QPushButton,QStylePainter,QStyleOptionButton,QStyle
import native,store,source_gateway
from professional_components import triple,action_button,InfoCard
from vci_workspace import Workspace as ConnectionWorkspace

def text(ar,fr,en):return triple(ar,fr,en)
class BrandTile(QPushButton):
 def __init__(self,name):
  super().__init__(name);self.setAccessibleName(name);self.setMinimumHeight(88)
 def paintEvent(self,event):
  painter=QStylePainter(self);option=QStyleOptionButton();self.initStyleOption(option);option.text='';option.icon=QIcon();painter.drawControl(QStyle.CE_PushButton,option)
  pix=self.icon().pixmap(self.iconSize());painter.drawPixmap((self.width()-pix.width())//2,14,pix)
  painter.setPen(self.palette().buttonText().color());label=self.fontMetrics().elidedText(self.text(),Qt.ElideRight,max(1,self.width()-16));painter.drawText(8,44,self.width()-16,self.height()-48,Qt.AlignCenter,label)

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
  super().__init__();self.window=window;self.worker=None;self.actions=[];root=QVBoxLayout(self);self.tabs=QStackedWidget();self.tabs.setMaximumHeight(520);root.addWidget(self.tabs,1);brands=QWidget();details=QWidget();self.tabs.addWidget(brands);self.stage_pages={}
  for key in ('model','year','engine'):
   page=QWidget();layout=QVBoxLayout(page);layout.setAlignment(Qt.AlignTop);self.stage_pages[key]=layout;self.tabs.addWidget(page)
  self.tabs.addWidget(details);self.catalog=[];self.selected_definition=None
  import vehicle_definitions
  try:self.catalog=vehicle_definitions.load(store.BASE/'vehicle-definitions.json')
  except (OSError,ValueError) as error:self.catalog_error=str(error)
  navigation=QHBoxLayout();back=action_button(text('رجوع','Retour','Back'));back.clicked.connect(lambda:self.tabs.setCurrentIndex(max(0,self.tabs.currentIndex()-1)));self.back=back;navigation.addWidget(back);self.stage_title=QLabel(text('الماركة ← الموديل ← السنة ← المحرك ← مراجعة','Marque → Modèle → Année → Moteur → Révision','Make → Model → Year → Engine → Review'));self.stage_title.setWordWrap(True);navigation.addWidget(self.stage_title,1);root.insertLayout(0,navigation);brand_layout=QVBoxLayout(brands);detail_layout=QVBoxLayout(details);self.search=QLineEdit();self.search.setPlaceholderText(text('ابحث عن الماركة','Rechercher une marque','Search makes'));brand_layout.addWidget(self.search)
  self.favorites=set(store.cache('vehicle_favorites') or []);self.only_favorites=QCheckBox(text('المفضلة فقط','Favoris seulement','Favorites only'));brand_layout.addWidget(self.only_favorites)
  self.scroll=QScrollArea();self.scroll.setWidgetResizable(True);brand_layout.addWidget(self.scroll,1);container=QWidget();self.grid=QGridLayout(container);self.scroll.setWidget(container);self.buttons={}
  importer=action_button(text('استيراد تعريفات الموديلات والسنوات والمحركات','Importer les définitions véhicules','Import sourced vehicle definitions'));importer.clicked.connect(self.import_definitions);detail_layout.addWidget(importer)
  base=Path(native.__file__).parent
  if logos is None:
   try:logos=json.loads((base/'data/logos.json').read_text())
   except (OSError,ValueError):logos={}
  for name,data in logos.items():
   button=BrandTile(name);button.setObjectName('vehicleBrand');button.setIconSize(QSize(32,24));pix=QPixmap(str(base/str(data.get('path','')).lstrip('/')))
   if not pix.isNull():
    # Source brand marks are often black; a neutral tile stays readable in both themes.
    logo=pix.scaled(28,20,Qt.KeepAspectRatio,Qt.SmoothTransformation);tile=QPixmap(32,24);tile.fill(Qt.transparent);painter=QPainter(tile);painter.setRenderHint(QPainter.Antialiasing);painter.setPen(Qt.NoPen);painter.setBrush(QColor('#f4f6f8'));painter.drawRoundedRect(0,0,32,24,3,3);painter.drawPixmap((32-logo.width())//2,(24-logo.height())//2,logo);painter.end();button.setIcon(QIcon(tile))
   button.setCheckable(True);button.clicked.connect(lambda checked=False,n=name:self.choose_make(n));self.buttons[name]=button
  self.search.textChanged.connect(self.reflow);self.only_favorites.toggled.connect(self.reflow)
  self.fields={};row=QHBoxLayout();detail_layout.addLayout(row,1);identity=InfoCard(text('هوية السيارة','Identité véhicule','Vehicle identity'));row.addWidget(identity,3);identity.body.setAlignment(Qt.AlignTop);identity.setMaximumHeight(380);form=QFormLayout();identity.body.addLayout(form);image_card=InfoCard(text('صورة السيارة المختارة','Photo du véhicule','Selected vehicle photo'));row.addWidget(image_card,2);image_card.setMaximumHeight(380);self.photo=QLabel();self.photo.setAlignment(Qt.AlignCenter);self.photo.setMinimumSize(160,130);self.photo.setWordWrap(True);image_card.body.addWidget(self.photo,1);self.photo_path='';self.photo_identity=None;attach=action_button(text('إضافة صورة السيارة','Ajouter une photo','Attach vehicle photo'));attach.clicked.connect(self.attach_photo);image_card.body.addWidget(attach);self.summary=QLabel();self.summary.setWordWrap(True);image_card.body.addWidget(self.summary)
  saved=dict(getattr(window,'vehicle',{}) or store.cache('vehicle_selection') or {})
  if saved and not getattr(window,'vehicle',{}):window.vehicle=dict(saved)
  for key,label in [('make',text('الماركة','Marque','Make')),('model',text('الموديل','Modèle','Model')),('year',text('السنة','Année','Year')),('engine',text('المحرك','Moteur','Engine')),('vin','VIN'),('fuel',text('نوع الطاقة / الوقود','Énergie / carburant','Powertrain / fuel'))]:
   value=str(saved.get(key,'') or '');choices=[] if key=='year' else ['Gasoline','Diesel','Electric','Hybrid','Plug-in hybrid','LPG','CNG','Ethanol','Hydrogen','Other'] if key=='fuel' else [];entry=Choice(value,choices) if key in ('model','year','engine','fuel') else QLineEdit(value);entry.setObjectName('vehicle_'+key);form.addRow(label,entry);self.fields[key]=entry
  self.photo_path=saved.get('photo_path','');self.photo_identity=saved.get('photo_identity')
  for field in self.fields.values():field.textChanged.connect(self.refresh_state)
  self.refresh_state()
  self.consent=QCheckBox(text('أوافق على إرسال VIN إلى NHTSA','Autoriser l’envoi du VIN à NHTSA','Allow sending VIN to NHTSA'));detail_layout.addWidget(self.consent)
  actions=QHBoxLayout();root.addLayout(actions)
  for label,fn in [(text('اعتماد الاختيار','Enregistrer sélection','Save selection'),self.save_selection),(text('تبديل المفضلة','Basculer favori','Toggle favorite'),self.favorite),(text('بحث VIN','Rechercher VIN','Look up VIN'),self.lookup)]:
   b=action_button(label);b.clicked.connect(fn);actions.addWidget(b);self.actions.append(b)
  self.vin_candidate=None;self.vin_apply=action_button(text('اعتماد بيانات VIN المعروضة','Appliquer les données VIN','Apply displayed VIN identity'));self.vin_apply.setEnabled(False);self.vin_apply.hide();self.vin_apply.clicked.connect(self.apply_vin);detail_layout.addWidget(self.vin_apply)
  self.status=QLabel();root.addWidget(self.status);scope=QLabel(text('اختيار يدوي؛ دعم وحدات OEM غير مثبت. OBD عام حسب المحول والسيارة.','Sélection manuelle ; support OEM non établi. OBD générique selon véhicule et adaptateur.','Manual identity; OEM module support is not established. Generic OBD depends on vehicle and adapter.'));scope.setWordWrap(True);self.scope=scope;root.addWidget(scope)
  self.log=QTextEdit();self.log.setReadOnly(True);self.log.setMaximumHeight(70);self.log.hide();root.addWidget(self.log);self.reflow();self.tabs.currentChanged.connect(self.stage_actions);self.stage_actions()
 def stage_actions(self,*args):
  index=self.tabs.currentIndex();self.back.setVisible(index>0);self.tabs.setMaximumHeight(520 if index==4 else 16777215)
  titles=[text('اختيار الماركة','Choisir la marque','Choose make'),text('اختيار الموديل','Choisir le modèle','Choose model'),text('اختيار السنة','Choisir l’année','Choose year'),text('اختيار المحرك','Choisir le moteur','Choose engine'),text('مراجعة السيارة','Vérifier le véhicule','Review vehicle')]
  self.stage_title.setText(titles[index]);self.scope.setVisible(index==4)
  for button in self.actions:button.setVisible(index==4)
  self.actions[0].setEnabled(index==4 and self.worker is None)
 def import_definitions(self):
  import vehicle_definitions
  filename,_=QFileDialog.getOpenFileName(self,text('تعريفات سيارات مع مصادر','Définitions avec sources','Vehicle definitions with sources'),'','JSON (*.json)')
  if not filename:return
  try:
   rows=vehicle_definitions.load(filename);destination=store.BASE/'vehicle-definitions.json';destination.parent.mkdir(parents=True,exist_ok=True)
   if destination.exists():destination.with_suffix('.json.backup').write_bytes(destination.read_bytes())
   destination.write_text(json.dumps(rows,ensure_ascii=False,indent=2));self.catalog=rows;self.status.setText(text('استيراد مراجع فقط؛ لا يثبت دعم التشخيص','Références importées ; diagnostic non vérifié','References imported; diagnostic compatibility not verified'))
  except (ValueError,OSError) as error:self.error(str(error))
 def stage(self,key,title,options,callback,manual):
  layout=self.stage_pages[key]
  while layout.count():
   item=layout.takeAt(0)
   if item.widget():item.widget().deleteLater()
  heading=QLabel(title);heading.setObjectName('heading');heading.setWordWrap(True);layout.addWidget(heading)
  if self.selected_definition:
   source=QLabel(str(self.selected_definition.get('source',''))+' · '+str(self.selected_definition.get('market','')));source.setWordWrap(True);layout.addWidget(source)
  if options:
   area=QScrollArea();area.setWidgetResizable(True);container=QWidget();items=QVBoxLayout(container)
   for label,value in options:
    button=action_button(label);button.clicked.connect(lambda checked=False,value=value:callback(value));items.addWidget(button)
   items.addStretch();area.setWidget(container);layout.addWidget(area,1)
  else:
   empty=QLabel(text('لا توجد بيانات موثقة لهذه المرحلة؛ استخدم الإدخال اليدوي','Aucune donnée documentée ; saisie manuelle disponible','No documented entries for this step; manual entry available'));empty.setWordWrap(True);layout.addWidget(empty)
  button=action_button(text('إدخال يدوي — بيانات غير متحقق منها','Saisie manuelle — non vérifiée','Manual entry — unverified'));button.clicked.connect(manual);layout.addWidget(button)
  self.tabs.setCurrentIndex({'model':1,'year':2,'engine':3}[key])
 def choose_make(self,make):
  import vehicle_definitions
  if self.fields['make'].text().casefold()!=make.casefold():
   for key in ('model','year','engine','fuel'):self.fields[key].setText('')
  self.fields['make'].setText(make);self.selected_definition=None
  rows=vehicle_definitions.models(self.catalog,make)
  self.stage('model',make+' · '+text('اختر الموديل والجيل والسوق','Modèle, génération et marché','Model, generation and market'),[(r['model']+' · '+r['generation']+' · '+r['market'],r) for r in rows],self.choose_model,lambda:self.manual_stage('model',self.manual_year))
 def choose_model(self,row):
  self.selected_definition=row;self.fields['model'].setText(row['model']+' '+row['generation']);self.fields['year'].setText('');self.fields['engine'].setText('');self.fields['fuel'].setText('')
  self.stage('year',text('سنوات الموديل المسجلة في المصدر','Années documentées du modèle','Documented model years'),[(str(y),y) for y in sorted(set(row['years']),reverse=True)],self.choose_year,lambda:self.manual_stage('year',self.manual_engine))
 def choose_year(self,year):
  import vehicle_definitions
  self.fields['year'].setText(str(year));self.fields['engine'].setText('');self.fields['fuel'].setText('')
  engines=vehicle_definitions.engines(self.selected_definition,year)
  self.stage('engine',text('المحركات المرتبطة بالموديل والسنة','Moteurs du modèle et de cette année','Engines for this model and year'),[(e['name']+' · '+e['fuel'],e) for e in engines],self.choose_engine,lambda:self.manual_stage('engine',lambda:self.tabs.setCurrentIndex(4)))
 def choose_engine(self,engine):
  self.fields['engine'].setText(engine['name']);self.fields['fuel'].setText(engine['fuel']);self.tabs.setCurrentIndex(4)
 def manual_stage(self,key,next_step):
  self.selected_definition=None;layout=self.stage_pages[key]
  while layout.count():
   item=layout.takeAt(0)
   if item.widget():item.widget().deleteLater()
  note=QLabel(text('إدخال الفني؛ لا يثبت توافق السيارة أو سنوات الإنتاج','Saisie du technicien ; compatibilité non établie','Technician entry; does not establish compatibility or production years'));note.setWordWrap(True);layout.addWidget(note);entry=QLineEdit(self.fields[key].text());entry.textChanged.connect(self.fields[key].setText);layout.addWidget(entry)
  button=action_button(text('التالي','Suivant','Next'));button.clicked.connect(next_step);layout.addWidget(button);self.tabs.setCurrentIndex({'model':1,'year':2,'engine':3}[key])
 def manual_year(self):self.manual_stage('year',self.manual_engine)
 def manual_engine(self):self.manual_stage('engine',lambda:self.tabs.setCurrentIndex(4))
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
  self.vin_candidate=(vin,result);self.vin_apply.setEnabled(True);self.vin_apply.show();self.log.show();self.log.setPlainText(json.dumps(result,ensure_ascii=False,indent=2));self.tabs.setCurrentIndex(4)
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
