"""Exercise native wallpaper synchronization and desktop-window classification."""
import os,sys,importlib.util,tempfile
from pathlib import Path
from unittest.mock import patch
os.environ['GITM_NATIVE_PLASMA']='1'
sys.path.insert(0,str(Path('output/GITM-OS-3.3/app').resolve()))
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage,QColor
from PySide6.QtWidgets import QApplication
spec=importlib.util.spec_from_file_location('gitm_desktop_probe','plasma-transition/patches/gitm_desktop.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.ROOT=Path('output/GITM-OS-3.3/app').resolve()
sys.path.insert(0,str(Path('design-build').resolve()))
app=QApplication([])
with tempfile.TemporaryDirectory() as directory:
 home=Path(directory);m.STATE=home/'state';(home/'.config').mkdir();image=home/'wallpaper.png'
 picture=QImage(24,24,QImage.Format_RGB32);picture.fill(QColor('#345678'));assert picture.save(str(image))
 (home/'.config/plasma-org.kde.plasma.desktop-appletsrc').write_text('[Containments][1][Wallpaper][org.kde.image][General]\nImage='+image.as_uri()+'\n')
 with patch.object(Path,'home',return_value=home):
  w=m.Desktop();w.refresh()
  assert not w.testAttribute(Qt.WA_X11NetWmWindowTypeDesktop)
  assert w._native_wallpaper_path==str(image)
  assert w.wallpaper.width()==24 and w.wallpaper.height()==24
  assert (m.STATE/'wallpaper-path.txt').read_text()==str(image)
  w.close()
print('Native wallpaper selection synchronized; desktop window classification verified')
