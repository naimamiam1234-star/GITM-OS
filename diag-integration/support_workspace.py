"""Useful requirements/coverage pages; unavailable operations never execute."""
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QLabel,QTabWidget
from professional_components import triple as t,InfoCard,MetricCard,action_button
SERVICE=[(('المحرك','Moteur','Engine'),['DPF','EGR','Injector','Throttle']), (('الفرامل','Freins','Brakes'),['ABS Bleed','EPB']), (('التوجيه','Direction','Steering'),['SAS']), (('الكهرباء','Électricité','Electrical'),['BMS','Battery registration']), (('الدورية','Périodique','Periodic'),['Oil reset','Service interval']), (('الهيكل','Carrosserie','Body'),['Suspension','Windows','Seats']), (('الإطارات','Pneus','Tyres'),['TPMS'])]

def show(window,kind='service'):
 title='TPMS' if kind=='tpms' else t('وظائف الصيانة','Fonctions entretien','Service functions');layout=window.page(title);widget=QWidget();root=QVBoxLayout(widget);layout.addWidget(widget)
 header=InfoCard(title);message=QLabel(t('حالة الدعم: غير متاح للتنفيذ. يلزم تعريف ECU مطابق ومحول أو عتاد متوافق واختبار فعلي.','Exécution indisponible. Profil ECU exact, matériel compatible et test véhicule requis.','Execution unavailable. Exact ECU definitions, compatible hardware and vehicle validation are required.'));message.setWordWrap(True);header.body.addWidget(message);root.addWidget(header)
 if kind=='tpms':
  grid=QGridLayout();root.addLayout(grid)
  for i,pos in enumerate([t('أمامي يسار','Avant gauche','Front left'),t('أمامي يمين','Avant droit','Front right'),t('خلفي يسار','Arrière gauche','Rear left'),t('خلفي يمين','Arrière droit','Rear right')]):
   card=MetricCard(pos,'—',t('الضغط / الحرارة / هوية الحساس: لا توجد قراءة','Pression / température / ID: aucune mesure','Pressure / temperature / sensor ID: no measurement'));grid.addWidget(card,i//2,i%2)
  note=QLabel(t('قراءة وبرمجة RF تتطلب أداة TPMS متوافقة؛ إعادة التعلم عبر ECU تعتمد على طراز السيارة. لا تُعرض بيانات تعليمية كقياسات فعلية.','RF nécessite un outil TPMS compatible; apprentissage ECU dépend du véhicule.','RF reading/programming requires compatible TPMS equipment; ECU relearn depends on vehicle coverage.'));note.setWordWrap(True);root.addWidget(note);b=action_button(t('برمجة الحساسات: غير متاحة','Programmation indisponible','Sensor programming unavailable'));b.setEnabled(False);root.addWidget(b)
 else:
  tabs=QTabWidget();root.addWidget(tabs,1)
  for group,names in SERVICE:
   page=QWidget();grid=QGridLayout(page)
   for i,name in enumerate(names):
    card=InfoCard(name);label=QLabel(t('غير متاح · يلزم التحقق من الوحدة وشروط الإجراء','Indisponible · calculateur et procédure à valider','Unavailable · ECU and procedure must be verified'));label.setWordWrap(True);card.body.addWidget(label);b=action_button(t('تنفيذ غير متاح','Exécution indisponible','Execution unavailable'));b.setEnabled(False);card.body.addWidget(b);grid.addWidget(card,i//2,i%2)
   tabs.addTab(page,t(*group))
 root.addStretch();return widget
