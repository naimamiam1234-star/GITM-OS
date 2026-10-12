"""Separate system updates from verified application packages."""
import json,tempfile
from pathlib import Path
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QTextBrowser,QFileDialog,QMessageBox,QCheckBox,QProgressBar
from professional_components import triple,action_button,MetricCard,InfoCard
import usb_update,workshop_tools
from diagnostic_workspace import Worker

def inspect_package(path):
 with tempfile.TemporaryDirectory() as directory:
  manifest,_=usb_update.inspect(path,Path(directory))
  return {'version':manifest['version'],'files':len(manifest['files']),'kind':manifest['kind']}

class Updates(QWidget):
 def __init__(self,window):
  super().__init__();self.window=window;self.selected_path=None;self.worker=None;layout=QVBoxLayout(self);release=usb_update.release()
  self.version=MetricCard(triple('الإصدار المثبت','Version installée','Installed version'),str(release.get('version','—')));layout.addWidget(self.version)
  system=InfoCard(triple('تحديثات النظام','Mises à jour système','System updates'));description=QLabel(triple('استخدم مدير تحديثات Plasma للنواة وحزم النظام.','Utilisez le gestionnaire Plasma pour le noyau et les paquets système.','Use Plasma’s update manager for kernel and system packages.'));description.setWordWrap(True);system.body.addWidget(description);discover=action_button(triple('فتح Discover','Ouvrir Discover','Open Discover'));discover.clicked.connect(lambda:workshop_tools.launch(window,'plasma-discover','--mode','update'));system.body.addWidget(discover);layout.addWidget(system)
  app=InfoCard(triple('حزم تطبيق GITM الموقعة','Paquets GITM signés','Signed GITM application packages'));scope=QLabel(triple('حزم محلية .gitmupdate للواجهة والبيانات فقط. احتفظ بتخزين دائم في جلسة Live.','Paquets locaux .gitmupdate pour l’interface et les données. Stockage persistant requis en session Live.','Local .gitmupdate packages update the interface and data. Live sessions require persistent storage.'));scope.setWordWrap(True);app.body.addWidget(scope);layout.addWidget(app)
  row=QHBoxLayout();self.select=action_button(triple('اختيار وفحص','Choisir et vérifier','Select and verify'));self.select.clicked.connect(self.choose);row.addWidget(self.select);self.install=action_button(triple('تثبيت','Installer','Install'),role='primary');self.install.setEnabled(False);self.install.clicked.connect(self.apply);row.addWidget(self.install);self.rollback=action_button(triple('رجوع','Restaurer','Rollback'));self.rollback.setEnabled(bool(release.get('previous')));self.rollback.clicked.connect(self.restore);row.addWidget(self.rollback);app.body.addLayout(row)
  self.feedback=QLabel(triple('بانتظار حزمة محلية','En attente d’un paquet local','Waiting for a local package'));self.feedback.setWordWrap(True);app.body.addWidget(self.feedback);self.progress=QProgressBar();self.progress.setRange(0,1);self.progress.setValue(0);app.body.addWidget(self.progress)
  details=QCheckBox(triple('تفاصيل تقنية','Détails techniques','Technical details'));layout.addWidget(details);self.raw=QTextBrowser();self.raw.hide();layout.addWidget(self.raw);details.toggled.connect(self.raw.setVisible);layout.addStretch()
 def work(self,fn,done):
  window=self.window
  if self.worker or getattr(window,'_obd_worker',None) is not None or (getattr(window,'task',None) is not None and window.task.isRunning()):return False
  self.select.setEnabled(False);self.install.setEnabled(False);self.rollback.setEnabled(False);self.progress.setRange(0,0);self.worker=Worker(lambda cancel,progress:fn(),window);window._obd_worker=self.worker
  from shiboken6 import isValid
  self.worker.result.connect(lambda value:done(value) if isValid(self) else None);self.worker.failure.connect(lambda error:self.failed(error) if isValid(self) else None)
  def finished():
   window._obd_worker=None
   if isValid(self):self.worker=None;self.select.setEnabled(True);self.rollback.setEnabled(bool(usb_update.release().get('previous')));self.progress.setRange(0,1)
  self.worker.finished.connect(finished);self.worker.start();return True
 def failed(self,error):
  self.selected_path=None;self.install.setEnabled(False);self.feedback.setText(triple('فشل التحقق أو العملية','Échec de vérification ou opération','Verification or operation failed'));self.raw.setPlainText(str(error));self.raw.show();self.progress.setValue(0)
 def choose(self):
  path,_=QFileDialog.getOpenFileName(self,'GITM','/media','GITM (*.gitmupdate)')
  if path:self.verify(path)
 def verify(self,path):
  self.selected_path=None;self.install.setEnabled(False)
  def checked(value):
   self.selected_path=path;self.install.setEnabled(True);self.progress.setValue(1);self.feedback.setText(triple('التوقيع والملفات سليمة','Signature et fichiers vérifiés','Signature and files verified')+' · '+str(value['version']));self.raw.setPlainText(json.dumps(value,ensure_ascii=False,indent=2))
  self.work(lambda:inspect_package(path),checked)
 def completed(self,result):
  self.selected_path=None;self.install.setEnabled(False);self.progress.setValue(1);self.version.set_value(str(usb_update.release().get('version','—')));self.feedback.setText(triple('تم · أعد تشغيل التطبيق','Terminé · Redémarrez l’application','Complete · Restart the application'));self.raw.setPlainText(str(result))
 def apply(self):
  path=self.selected_path
  if path and QMessageBox.question(self,'GITM',triple('تثبيت الحزمة الموثقة؟','Installer le paquet vérifié ?','Install the verified package?'))==QMessageBox.Yes:self.work(lambda:workshop_tools.run_update('install',path),self.completed)
 def restore(self):
  if QMessageBox.question(self,'GITM',triple('استعادة الإصدار السابق؟','Restaurer la version précédente ?','Restore the previous version?'))==QMessageBox.Yes:self.work(lambda:workshop_tools.run_update('rollback'),self.completed)

def show(window):
 layout=window.page(triple('مركز التحديثات','Centre de mises à jour','Update center'));widget=Updates(window);layout.addWidget(widget);return widget
