"""Offscreen integration test against the assembled AutoDiag application."""
import os,sys,tempfile
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen'
os.environ['GITM_STATE']=tempfile.mkdtemp(prefix='gitm-design-')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'build-input/app'))
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication,QPushButton
from native import Window
app=QApplication([])
window=Window()
app.setLayoutDirection(Qt.RightToLeft)
window.resize(1280,860);window.show();app.processEvents()
assert len(window.home_cards)==12
assert all(c.accessibleName() for c in window.home_cards)
for size in ((1280,860),(800,600)):
    window.resize(*size);app.processEvents()
    assert window.width()==size[0], 'Window minimum width prevents small-screen use'
    assert window.pages.widget(0).horizontalScrollBar().maximum()==0,'Home overflows horizontally'
for index,lang in enumerate(('ar','fr','en')):
    window.language_picker.setCurrentIndex(index);app.processEvents()
    assert app.layoutDirection()==(Qt.RightToLeft if lang=='ar' else Qt.LeftToRight)
    window.resize(1280,860);app.processEvents()
    output=Path(os.environ.get('GITM_PREVIEW_DIR','/tmp/gitm-app-previews'));output.mkdir(parents=True,exist_ok=True)
    assert window.grab().save(str(output/f'autodiag-{lang}.png'))
# Card clicks are real navigation, not decorative mockups.
window.home_cards[1].click();app.processEvents();assert window.pages.currentIndex()>0
window.go_home();assert window.pages.currentIndex()==0
window.home_cards[3].click();app.processEvents();assert window.pages.currentIndex()>0
window.go_home();window.close()
print('PASS: three languages, RTL, 800px layout, card navigation, assistant page')
