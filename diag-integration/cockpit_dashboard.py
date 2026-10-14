"""Vehicle-session cockpit. Only measured session ECU rows are displayed."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QLabel,QListWidget,QMenu,QSizePolicy
from vehicle_silhouette import VehicleSilhouette
from professional_components import InfoCard,action_button,icon,triple as t

class Cockpit(QWidget):
 def __init__(self,shell):
  super().__init__();self.shell=shell;self.signature=None
  root=QVBoxLayout(self);root.setContentsMargins(16,14,16,14);root.setSpacing(14)
  identity=InfoCard(t('السيارة والجلسة الحالية','Véhicule et session','Vehicle and current session'));root.addWidget(identity)
  row=QHBoxLayout();identity.body.addLayout(row)
  emblem=VehicleSilhouette();emblem.setMinimumSize(90,120);emblem.setMaximumSize(110,130);row.addWidget(emblem)
  detail=QVBoxLayout();row.addLayout(detail,1);self.vehicle_label=QLabel();self.vehicle_label.setObjectName('heading');self.vehicle_label.setWordWrap(True);detail.addWidget(self.vehicle_label)
  self.home_state=QLabel();self.home_state.setWordWrap(True);detail.addWidget(self.home_state)
  buttons=QVBoxLayout();row.addLayout(buttons);self.home_actions={}
  for key,label,ico in [('vehicle',t('اختيار السيارة','Choisir véhicule','Choose vehicle'),'car'),('adapter',t('ربط المحول','Connecter VCI','Connect adapter'),'engine')]:
   b=action_button(label,icon=ico);b.clicked.connect(lambda checked=False,k=key:shell.navigate(k));buttons.addWidget(b);self.home_actions[key]=b
  visit=action_button(t('الزيارة الحالية','Visite actuelle','Current visit'),icon='history');menu=QMenu(visit)
  menu.addAction(t('استكمال الزيارة','Reprendre','Resume visit'),lambda:shell.begin_visit(True));menu.addAction(t('زيارة جديدة','Nouvelle visite','New visit'),lambda:shell.begin_visit(False));visit.setMenu(menu);buttons.addWidget(visit)
  workspace=QHBoxLayout();root.addLayout(workspace,5)
  main=InfoCard(t('وحدات التحكم الإلكترونية','Calculateurs électroniques','Electronic control units'));workspace.addWidget(main,5)
  self.explanation=QLabel();self.explanation.setWordWrap(True);main.body.addWidget(self.explanation)
  self.diagram=QWidget();diagram_layout=QHBoxLayout(self.diagram);diagram_layout.setContentsMargins(10,0,10,0);diagram_layout.setSpacing(24)
  self.nodes=QWidget();self.grid=QGridLayout(self.nodes);self.grid.setSpacing(16);diagram_layout.addWidget(self.nodes,2)
  center=QVBoxLayout();silhouette=VehicleSilhouette();center.addWidget(silhouette,1,Qt.AlignHCenter)
  caption=QLabel(t('تمثيل عام للمركبة','Schéma générique','Generic vehicle schematic'));caption.setObjectName('muted');caption.setAlignment(Qt.AlignCenter);center.addWidget(caption);diagram_layout.addLayout(center,1)
  self.empty=QLabel(t('لم تُكتشف وحدات بعد\nاربط المحول وحدد السيارة ثم افتح الفحص','Aucun calculateur détecté\nConnecter et identifier le véhicule','No ECUs detected yet\nConnect the adapter and identify the vehicle'));self.empty.setAlignment(Qt.AlignCenter);self.empty.setWordWrap(True);self.empty.setMinimumWidth(140);diagram_layout.addWidget(self.empty,2);main.body.addWidget(self.diagram,1)
  scan=action_button(t('فتح الفحص','Ouvrir le diagnostic','Open diagnostic scan'),'primary',icon='smart');scan.setMaximumWidth(320);scan.clicked.connect(lambda:shell.navigate('diagnosis'));scan.setMinimumWidth(260);main.body.addWidget(scan,0,Qt.AlignHCenter);self.home_actions['diagnosis']=scan
  assistant=InfoCard(t('تحليل الجلسة','Analyse de session','Session analysis'));assistant.setMaximumWidth(240);workspace.addWidget(assistant,1)
  mark=QLabel();mark.setPixmap(icon('ai').pixmap(56,56));mark.setAlignment(Qt.AlignCenter);assistant.body.addWidget(mark)
  note=QLabel(t('افتح المساعد لتحليل أعطال وقياسات هذه الجلسة.','Analyser les défauts et mesures de cette session.','Analyze faults and measurements from this session.'));note.setWordWrap(True);assistant.body.addWidget(note);assistant.body.addStretch()
  ai=action_button(t('المساعد','Assistant','Assistant'),icon='ai');ai.clicked.connect(shell.show_assistant);assistant.body.addWidget(ai);self.home_actions['ai']=ai
  stages=InfoCard(t('مراحل الجلسة','Étapes de session','Session stages'));root.addWidget(stages)
  self.stage=QLabel();self.stage.setWordWrap(True);stages.body.addWidget(self.stage)
  history=InfoCard(t('السيارات والزيارات السابقة','Véhicules et visites précédentes','Previous vehicles and visits'));root.addWidget(history,2)
  self.vehicle_records=QListWidget();self.vehicle_records.setMaximumHeight(112);self.vehicle_records.setMinimumHeight(0);self.vehicle_records.itemActivated.connect(shell.restore_vehicle);history.body.addWidget(self.vehicle_records)
  self.no_vehicles=QLabel(t('لم تُحفظ سيارة بعد؛ ابدأ زيارة لحفظ الملف.','Démarrer une visite pour enregistrer le véhicule.','Start a visit to save the vehicle profile.'));self.no_vehicles.setWordWrap(True);history.body.addWidget(self.no_vehicles)
  self.recents=QLabel();self.recents.setWordWrap(True);self.recents.setObjectName('muted');history.body.addWidget(self.recents)
 def update_session(self,vehicle,info,report):
  valid=bool(report and report.get('vehicle')==vehicle)
  ecus=report.get('ecus',[]) if valid else []
  if valid and report.get('evidence')=='simulator':self.home_state.setText(t('محاكاة · نتائج مختبر افتراضي وليست سيارة فعلية','Simulation · aucune voiture réelle','Simulator · virtual laboratory, not a physical vehicle'))
  state=t('قراءة مسجلة','Lecture enregistrée','Recorded reading') if valid else t('لم تُقرأ الأعطال بعد','Défauts non lus','Faults not read yet')
  self.stage.setText(('✓ ' if all(vehicle.get(k) for k in ('make','model','year')) else '○ ')+t('هوية السيارة','Identité véhicule','Vehicle identity')+'   →   '+('✓ ' if info.get('connected') else '○ ')+t('اتصال المحول','Connexion VCI','Adapter connection')+'   →   '+state)
  self.explanation.setText(t('النتائج من الجلسة المطابقة فقط؛ لا تثبت قراءة OBD توفر جميع وحدات السيارة.','Résultats de la session correspondante uniquement.','Only matching session results; OBD readings do not establish complete ECU coverage.'))
  signature=repr([(e.get('id'),e.get('status')) for e in ecus])+str(valid)
  if signature==self.signature:return
  self.signature=signature
  while self.grid.count():
   item=self.grid.takeAt(0)
   if item.widget():item.widget().deleteLater()
  self.empty.setVisible(not ecus);self.nodes.setVisible(bool(ecus));self.vehicle_records.setVisible(self.vehicle_records.count()>0)
  for index,ecu in enumerate(ecus):
   card=InfoCard(str(ecu.get('id') or t('وحدة مستجيبة','Calculateur','Responding ECU')))
   label=QLabel(t('وحدة مستجيبة · راجع نتائج الفحص','Calculateur répondant · voir diagnostic','Responding ECU · review diagnostic results'));label.setWordWrap(True);card.body.addWidget(label)
   b=action_button(t('عرض النتائج','Voir résultats','View results'),icon='engine');b.clicked.connect(lambda:self.shell.navigate('diagnosis'));card.body.addWidget(b);card.setMaximumHeight(126);self.grid.addWidget(card,index,0)
