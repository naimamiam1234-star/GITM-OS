"""Regression: status controls open anchored popups, without launching settings."""
import os,sys
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
sys.path[:0]=[str(Path.cwd()/'plasma-transition/patches'),str(Path.cwd()/'patches')]
from PySide6.QtWidgets import QApplication,QPushButton
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from gitm_desktop import Desktop
app=QApplication([]);w=Desktop();w.resize(1280,800);w.show();app.processEvents()
launched=[];w.launch=lambda key,args:launched.append((key,args))
w.bluetooth();app.processEvents()
assert not launched,'Bluetooth status icon launched a full settings window'
popup=app.activePopupWidget()
assert popup and popup.isVisible(),'No actual Qt popup for Bluetooth'
assert popup.windowFlags() & Qt.FramelessWindowHint,'Popup has window decoration'
assert popup.y()>=w.status_buttons['bluetooth'].mapToGlobal(w.status_buttons['bluetooth'].rect().bottomLeft()).y()
QTest.keyClick(popup,Qt.Key_Escape);app.processEvents();assert not popup.isVisible();QTest.qWait(200)
# Qt closes an outside-clicked popup before replaying that click to its anchor.
w.bluetooth();app.processEvents();popup=app.activePopupWidget();popup.hide();w.bluetooth();app.processEvents()
assert not popup.isVisible(),'Replayed click reopened the same popup'
for key in ('volume','wifi'):
 w.status_buttons[key].click();app.processEvents()
 assert app.activePopupWidget() and app.activePopupWidget().isVisible(),key+' did not open a popup'
 assert not launched,key+' launched a full application'
w.power();app.processEvents();p=app.activePopupWidget();assert p and p.isVisible()
assert any(b.text()=='إيقاف التشغيل' for b in p.findChildren(QPushButton))
w.confirm_power('poweroff');app.processEvents();assert not launched,'Power executed before explicit confirmation'
assert any(b.text()=='إلغاء' for b in app.activePopupWidget().findChildren(QPushButton))
QTest.keyClick(app.activePopupWidget(),Qt.Key_Escape);app.processEvents();assert not launched
w.toggle_control();app.processEvents();assert app.activePopupWidget()==w.control
w.status_buttons['volume'].click();app.processEvents();assert not w.control.isVisible(),'Two panels remain open'
assert sum(p.isVisible() for p in w.popups.panels.values())==1
app.activePopupWidget().hide();w.appearance['mode']='light';w.apply_appearance();w.toggle_control();app.processEvents()
assert w.control.isVisible();assert 'لقطة شاشة' in [b.text() for b in w.control.findChildren(QPushButton)]
print('Anchored controls, Escape, single popup, day mode and explicit power confirmation passed')
w.radios.timer.stop();w.animation.stop();w.timer.stop()
