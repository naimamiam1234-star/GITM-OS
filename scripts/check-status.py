import os,sys,tempfile
from pathlib import Path
os.environ["QT_QPA_PLATFORM"]="offscreen"
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"patches"))
from PySide6.QtWidgets import QApplication
import desktop_radios as radios
assert radios.fields(r"*:Office\:WiFi:82:WPA2")==["*","Office:WiFi","82","WPA2"]
with tempfile.TemporaryDirectory() as folder:
 root=Path(folder);assert radios.battery(root)=="لا توجد بطارية"
 p=root/"BAT0";p.mkdir();(p/"type").write_text("Battery");(p/"capacity").write_text("74");(p/"status").write_text("Charging")
 assert radios.battery(root)=="74% · يشحن"
 (p/"present").write_text("0");assert radios.battery(root)=="لا توجد بطارية"
class FakeRadios(radios.QObject):
 changed=radios.Signal()
 def __init__(self,parent):
  super().__init__(parent);self.wifi="غير متصل";self.bluetooth="غير متوفر"
 def refresh(self):pass
 def show(self,kind):pass
radios.Radios=FakeRadios
import types
sys.modules["system_settings"]=types.SimpleNamespace(brightness_devices=lambda:[],metrics=lambda:{"disk_free":1,"disk_total":2,"ram_total":2,"ram_available":1})
import gitm_desktop
app=QApplication([]);w=gitm_desktop.Desktop();w.show();app.processEvents()
assert w.control.isHidden()
assert set(w.status_buttons)=={"wifi","bluetooth","battery","sync","search","chevron"}
assert all(not w.icon(x).isNull() for x in w.status_buttons)
assert not any(x[0]=="terminal" for x in gitm_desktop.APPS)
w.status_buttons["chevron"].click();app.processEvents();assert not w.control.isHidden()
w.resize(1100,800);app.processEvents();assert not w.control.isHidden()
w.status_buttons["chevron"].click();w.resize(1440,900);app.processEvents();assert w.control.isHidden()
Path("dist").mkdir(exist_ok=True);assert w.grab().save("dist/status-bar.png")
w.status_buttons["chevron"].click();app.processEvents();assert w.grab().save("dist/control-center.png")
print("STATUS_CONTROLS_PASSED: measured battery, escaped SSIDs, six icons, arrow-only panel, no terminal tile")
