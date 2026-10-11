import os,sys,tempfile,time,json
from pathlib import Path
os.environ.update(QT_QPA_PLATFORM='offscreen',GITM_STATE=tempfile.mkdtemp(),GITM_LANGUAGE='ar')
sys.path.insert(0,str(Path('gitm-current/build-input/app').resolve()))
from PySide6.QtWidgets import QApplication,QLineEdit,QPushButton,QLabel,QTextBrowser,QTextEdit,QCheckBox,QComboBox
from native import Window
import store,cloud_ui
app=QApplication([]);w=Window();w.resize(1280,900);w.show()
def ev():
 for _ in range(3):app.processEvents()
def click(text):
 b=next(b for b in w.pages.currentWidget().findChildren(QPushButton) if b.text()==text);b.click();ev()
def wait():
 while w.task and w.task.isRunning():ev();time.sleep(.01)
 ev()
def shot(name):ev();w.grab().save('autodiag-vnext-qa/'+name+'.png')
shot('home')
nav=[b.text() for b in w.findChildren(QPushButton) if b.objectName()=='navButton']
assert 'الإعدادات' not in nav and 'الفواتير' in nav
w.vehicle_details('RENAULT');fields=w.pages.currentWidget().findChildren(QLineEdit)
for f,v in zip(fields,['RENAULT','Megane','2020','1.5 dCi','']):f.setText(v)
click('اعتماد المركبة');assert w.vehicle['year']=='2020';shot('vehicle')
w.diagnosis_page();click('أكواد الأعطال');wait();assert 'تعذر' in w.diagout.toPlainText();shot('diagnosis')
w.dtc_page();w.pages.currentWidget().findChildren(QLineEdit)[0].setText('P0300');click('بحث');wait();assert 'P0300' in w.pages.currentWidget().findChild(QTextBrowser).toPlainText();shot('fault-reference')
w.service_page();assert all(not b.isEnabled() for b in w.pages.currentWidget().findChildren(QPushButton));shot('maintenance')
cloud_ui.save_session('test','اختبار سجل محلي',[{'role':'user','text':'P0300'}]);assert cloud_ui.sessions()[0][2][0]['text']=='P0300'
w.ai_page();click('إرسال');assert any('سجّل الدخول' in q.text() for q in w.pages.currentWidget().findChildren(QLabel));shot('assistant')
from autodiag_experience import render
assert '<script>' not in render({'value':'<script>'})
for index,name in [(0,'ar'),(1,'fr'),(2,'en')]:w.language_picker.setCurrentIndex(index);w.go_home();shot('home-'+name)
print('PASS navigation, vehicle persistence, disconnected diagnostics, DTC, service gating, local history, AI consent, HTML escaping, languages')
w.close();ev()
