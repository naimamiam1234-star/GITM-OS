"""Single GITM OS service handoff. General utilities stay outside AutoDiag."""
import sys,shutil,subprocess,os
from pathlib import Path
from PySide6.QtWidgets import QWidget,QVBoxLayout,QLabel,QMainWindow,QApplication
from PySide6.QtCore import Qt
from professional_components import triple as t,InfoCard,action_button,styles,icon
SERVICES={'calculator':('kcalc',('حاسبة النظام','Calculatrice système','System calculator')),'pdf':('okular',('قارئ PDF','Lecteur PDF','PDF reader')),'media':('vlc',('مشغل الوسائط','Lecteur multimédia','Media player')),'settings':('systemsettings',('إعدادات النظام','Paramètres système','System settings'))}

def command(kind,path=None):
 if kind in ('camera','updates'):return [sys.executable,str(Path(__file__).resolve()),kind]
 if kind not in SERVICES:raise ValueError('Unknown system service')
 cmd=[SERVICES[kind][0]]
 if path is not None:
  p=Path(path).expanduser().resolve()
  if not p.is_file():raise ValueError('Choose an existing local file')
  cmd.append(str(p))
 return cmd

def launch(window,kind,path=None):
 args=command(kind,path);env=os.environ.copy()
 if kind in SERVICES:
  env.pop('QT_STYLE_OVERRIDE',None);env.pop('QT_QPA_PLATFORMTHEME',None)
 subprocess.Popen(args,env=env)

def show(window,kind):
 labels=SERVICES.get(kind,('',('كاميرا النظام','Caméra système','System camera') if kind=='camera' else ('مركز تحديثات النظام','Centre de mises à jour système','System update center')))[1]
 l=window.page(t(*labels));widget=QWidget();root=QVBoxLayout(widget);l.addWidget(widget);card=InfoCard(t(*labels));root.addWidget(card)
 msg=QLabel(t('هذه خدمة مشتركة في GITM OS. يستخدمها AutoDiag دون إنشاء نسخة ثانية منها.','Service partagé de GITM OS, utilisé sans duplication par AutoDiag.','This shared GITM OS service is used by AutoDiag without duplicating the application.'));msg.setWordWrap(True);card.body.addWidget(msg)
 b=action_button(t('فتح خدمة النظام','Ouvrir le service système','Open system service'),'primary');b.clicked.connect(lambda:launch(window,kind));card.body.addWidget(b)
 if kind in SERVICES and not shutil.which(SERVICES[kind][0]):b.setEnabled(False);card.body.addWidget(QLabel(t('الخدمة غير مثبتة في هذه البيئة','Service non installé dans cet environnement','Service is not installed in this environment')))
 if kind=='camera':
  note=QLabel(t('بعد التصوير، اختر الملف لإرفاقه بتقرير الورشة. لا تُرسل الصور للسحابة تلقائيًا.','Après capture, choisir le fichier à joindre au rapport. Aucun envoi cloud automatique.','After capture, select the file to attach to a workshop report. No automatic cloud upload.'));note.setWordWrap(True);card.body.addWidget(note)
 root.addStretch();return widget

class ServiceWindow(QMainWindow):
 def __init__(self,kind):
  super().__init__();self.kind=kind;self.setWindowIcon(icon('camera' if kind=='camera' else 'update'));self.task=None;self._obd_worker=None;self.vehicle={};self.setWindowTitle('GITM OS · '+('Camera' if kind=='camera' else 'Update Center'));self.resize(1000,720);self.setMinimumSize(700,500);self.pages=None;self.current=None;self.state_label=QLabel()
  import system_settings
  pref=system_settings.preferences();dark=pref.get('theme')=='dark';self.setStyleSheet(styles(dark,pref.get('font_size',16)));self.build()
 def page(self,title):
  widget=QWidget();self.setCentralWidget(widget);l=QVBoxLayout(widget);l.setContentsMargins(20,20,20,20);heading=QLabel(title);heading.setObjectName('heading');l.addWidget(heading);return l
 def button(self,l,label,fn):
  b=action_button(label);b.clicked.connect(fn);l.addWidget(b);return b
 def output(self,l):
  from PySide6.QtWidgets import QTextEdit
  out=QTextEdit();out.setReadOnly(True);l.addWidget(out);return out
 def build(self):
  if self.kind=='updates':__import__('update_workspace').show(self);return
  try:
   from PySide6.QtMultimedia import QMediaDevices
  except ImportError:
   l=self.page(t('كاميرا GITM OS','Caméra GITM OS','GITM OS camera'));card=InfoCard(t('واجهة الكاميرا غير متاحة','Backend caméra indisponible','Camera backend unavailable'));message=QLabel(t('واجهة QtMultimedia غير مثبتة. ثبّت دعم الوسائط للكاميرا ثم أعد المحاولة.','QtMultimedia est absent. Installer le support multimédia puis réessayer.','QtMultimedia is not installed. Install the camera multimedia support and retry.'));message.setWordWrap(True);card.body.addWidget(message);l.addWidget(card);l.addStretch();return
  if QMediaDevices.videoInputs():
   import workshop_tools
   getattr(workshop_tools,"_system_camera_backend",workshop_tools.camera)(self)
   from PySide6.QtMultimedia import QCamera
   for cam in self.findChildren(QCamera):cam.errorOccurred.connect(lambda code,text:self.statusBar().showMessage(str(text)))
  else:
   l=self.page(t('كاميرا GITM OS','Caméra GITM OS','GITM OS camera'));card=InfoCard(t('لا توجد كاميرا متصلة','Aucune caméra connectée','No connected camera'));card.body.addWidget(QLabel(t('صِل كاميرا USB/V4L2 متوافقة ثم أعد البحث.','Connecter une caméra USB/V4L2 compatible puis actualiser.','Connect a compatible USB/V4L2 camera and refresh.')));b=action_button(t('البحث عن الكاميرات','Rechercher les caméras','Refresh cameras'),'primary');b.clicked.connect(self.build);card.body.addWidget(b);l.addWidget(card);l.addStretch()
 def closeEvent(self,event):
  if self._obd_worker is not None and self._obd_worker.isRunning():self._obd_worker.cancel.set();event.ignore();return
  if self.kind=='camera':
   try:
    from PySide6.QtMultimedia import QCamera
   except ImportError:QCamera=None
   if QCamera is not None:
    for cam in self.findChildren(QCamera):cam.stop()
  event.accept()
if __name__=='__main__':
 app=QApplication(sys.argv);from i18n import language
 from PySide6.QtNetwork import QLocalServer,QLocalSocket
 kind=sys.argv[1] if len(sys.argv)>1 else 'camera'
 if kind not in ('camera','updates'):raise SystemExit('Unknown OS service')
 name='gitm-os-'+kind+'-'+str(os.getuid());socket=QLocalSocket();socket.connectToServer(name)
 if socket.waitForConnected(300):socket.write(b'activate');socket.waitForBytesWritten(300);sys.exit(0)
 QLocalServer.removeServer(name);server=QLocalServer()
 if not server.listen(name):raise SystemExit('Could not start OS service')
 app.setApplicationName('GITM Camera' if kind=='camera' else 'GITM Update Center');app.setDesktopFileName('gitm-camera' if kind=='camera' else 'gitm-update');app.setWindowIcon(icon('camera' if kind=='camera' else 'update'))
 app.setLayoutDirection(Qt.RightToLeft if language()=='ar' else Qt.LeftToRight);window=ServiceWindow(kind)
 def activate():
  peer=server.nextPendingConnection();peer.disconnectFromServer();peer.deleteLater();window.showNormal();window.raise_();window.activateWindow()
 server.newConnection.connect(activate);window.show();sys.exit(app.exec())
