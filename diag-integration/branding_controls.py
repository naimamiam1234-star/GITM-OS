"""GITM desktop wallpaper and intro settings, using installed local assets."""
from pathlib import Path
import shutil
from PySide6.QtCore import Qt,QSize,QProcess,QProcessEnvironment
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QWidget,QVBoxLayout,QGridLayout,QScrollArea,QPushButton,QLabel,QCheckBox
import branding

def sync_native(desktop,path):
 if not path or not shutil.which('plasma-apply-wallpaperimage'):return
 path=Path(path)
 if not path.is_file():return
 process=QProcess(desktop);env=QProcessEnvironment.systemEnvironment();env.remove('QT_STYLE_OVERRIDE');env.remove('QT_QPA_PLATFORMTHEME');process.setProcessEnvironment(env);process.setProgram('plasma-apply-wallpaperimage');process.setArguments([str(path)]);process.finished.connect(process.deleteLater);process.start()

def show(desktop):
 from gitm_desktop import STATE
 desktop.popups.close();dialog,layout=desktop.panel('خلفيات وإقلاع GITM');dialog.resize(860,640);dialog.setLayoutDirection(Qt.RightToLeft)
 info=QLabel('الخلفيات والفيديوهات التي أرسلتها محفوظة محليًا. تقليل الحركة أو وضع الأداء يتجاوزان الفيديو.');info.setWordWrap(True);layout.addWidget(info)
 checkbox=QCheckBox('عرض فيديو بدء الجلسة');checkbox.setChecked(desktop.appearance.get('boot_video',True));checkbox.toggled.connect(lambda value:save_video(desktop,value));layout.addWidget(checkbox)
 reset=QPushButton('خلفية تلقائية حسب الوضع النهاري أو الليلي');reset.setMinimumHeight(44);reset.clicked.connect(lambda:select(desktop,None));layout.addWidget(reset)
 scroll=QScrollArea();scroll.setWidgetResizable(True);content=QWidget();grid=QGridLayout(content);scroll.setWidget(content);layout.addWidget(scroll,1)
 for i,row in enumerate(branding.wallpaper_choices()):
  button=QPushButton(('نهاري' if row['mode']=='light' else 'ليلي')+' · '+row.get('label',str(i+1)));button.setIcon(QIcon(str(row['file'])));button.setIconSize(QSize(184,104));button.setMinimumSize(240,148);button.setAccessibleName(button.text());button.clicked.connect(lambda checked=False,path=row['file']:select(desktop,path));grid.addWidget(button,i//3,i%3)
 dialog.show();return dialog
def save_video(desktop,value):desktop.appearance['boot_video']=bool(value);desktop.save_appearance()
def select(desktop,path):
 from gitm_desktop import STATE
 STATE.mkdir(parents=True,exist_ok=True);(STATE/'wallpaper-path.txt').write_text(str(path) if path else '')
 desktop.personal_wallpaper=str(path) if path else None
 if path:
  from PySide6.QtGui import QPixmap
  desktop.wallpaper=QPixmap(str(path))
 desktop.apply_appearance();sync_native(desktop,path or branding.default_wallpaper(desktop.appearance['mode']))
