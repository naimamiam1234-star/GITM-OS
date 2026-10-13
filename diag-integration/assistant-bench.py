"""Capture actual TCP simulator UI, never represented as a physical vehicle."""
import os,time,json,sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from i18n import change_language
import native,transport
from obd_simulator import Simulator

out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
app=QApplication([]);__import__('store').cache('settings',{'language':'ar'});app.setLayoutDirection(Qt.RightToLeft)
sim=Simulator().start();window=native.Window();window.vehicle={'make':'Renault','model':'SIMULATOR','year':'','engine':''};shell=window.professional_shell;shell.navigate('diagnosis');ws=window.diagnostic_workspace
try:
 transport.LINK.connect('wifi',f'127.0.0.1:{sim.port}',family='elm')
 report=ws.session.scan(vehicle=window.vehicle);ws.display(report);ws.connection_identity=ws.connection_key();window.resize(int(os.environ.get('GITM_BENCH_WIDTH','1600')),int(os.environ.get('GITM_BENCH_HEIGHT','1000')));window.show();app.processEvents();ws.tabs.setCurrentIndex(1)
 for row in range(ws.dtc.rowCount()):
  if ws.dtc.item(row,3).text()=='P0300':ws.dtc.selectRow(row);break
 shell.show_assistant();panel=shell.assistant_panel;panel.analyze()
 for theme in ('light','dark'):
  shell.set_theme(theme)
  for _ in range(15):app.processEvents();time.sleep(.01)
  window.grab().save(str(out/f'01-dtc-assistant-{theme}.png'))
 ws.tabs.setCurrentIndex(2);ws.ecus.setCurrentIndex(ws.ecus.findData('7E8'));ws.pids.setCurrentIndex(ws.pids.findData(12));ws.toggle_live()
 before=len(ws.samples);deadline=time.monotonic()+5
 while len(ws.samples)<before+4 and time.monotonic()<deadline:app.processEvents();time.sleep(.02)
 panel.capture();panel.analyze();app.processEvents();window.grab().save(str(out/'02-live-assistant-dark.png'))
 if len(ws.samples)<before+4:raise RuntimeError('Live acquisition did not continue with assistant open')
 panel.tabs.setCurrentIndex(1);app.processEvents();window.grab().save(str(out/'03-cloud-consent-preview.png'))
 panel.search('youtube');app.processEvents();window.grab().save(str(out/'04-search-settings-unconfigured.png'))
 panel.toggle_expanded();app.processEvents();window.grab().save(str(out/'05-assistant-expanded.png'));panel.toggle_expanded()
 ws.stop()
 deadline=time.monotonic()+5
 while ws.worker is not None and time.monotonic()<deadline:app.processEvents();time.sleep(.02)
 (out/'proof.json').write_text(json.dumps({'evidence':'simulator','session_id':report['id'],'sample_count':len(ws.samples),'reading_continues_with_panel':True,'external_services_configured':False,'vehicle_commands_from_assistant':False},indent=2))
finally:
 transport.LINK.close();sim.stop();window.close();app.processEvents()
