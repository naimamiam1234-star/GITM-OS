import unittest,sys,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
try:
 from PySide6.QtWidgets import QApplication,QWidget
 from diagnostic_workspace import Workspace
except ImportError:
 Workspace=None
@unittest.skipIf(Workspace is None,'Qt runtime not on Python path')
class WorkspaceTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
 def setUp(self):
  class Window(QWidget):
   vehicle={}
   def adapter_page(self):pass
  self.window=Window();self.ui=Workspace(self.window)
 def tearDown(self):self.ui.deleteLater();self.window.deleteLater();self.app.processEvents()
 def test_explicit_no_data(self):
  self.ui.display({'status':'partial','ecus':[{'id':'7E8','dtc':{'stored':{'status':'error','codes':[],'error':'NO DATA'}},'errors':['VIN unavailable']}],'errors':[{'section':'VIN','error':'NO DATA'}]})
  self.assertEqual(self.ui.dtc.item(0,3).text(),'NO DATA');self.assertIn('NO DATA',self.ui.summary.toPlainText())
 def test_bounded_recording_and_graph(self):
  self.ui.display({'status':'complete','ecus':[{'id':'7E8','supported_pids':[12]}]})
  self.ui.record.setChecked(True)
  self.ui.live_result([{'ecu':'7E8','pid':12,'value':n} for n in range(10001)])
  self.assertEqual(len(self.ui.samples),600);self.assertEqual(len(self.ui.recorded),10000);self.assertFalse(self.ui.record.isChecked());self.assertEqual(len(self.ui.graph.points),600);self.assertIn('10000' if '10000' in self.ui.status.text() else '10,000',self.ui.status.text())
 def test_graph_ecu_selection_is_stable(self):
  self.ui.display({'status':'complete','ecus':[{'id':'7E8','supported_pids':[12]},{'id':'7E9','supported_pids':[12]}]})
  self.ui.ecus.setCurrentIndex(self.ui.ecus.findData('7E8'))
  self.ui.live_result([{'ecu':'7E9','pid':12,'value':1900},{'ecu':'7E8','pid':12,'value':1700}])
  self.ui.live_result([{'ecu':'7E8','pid':12,'value':1750},{'ecu':'7E9','pid':12,'value':1950}])
  self.assertEqual(list(self.ui.graph.points),[1700,1750]);self.assertTrue(self.ui.graph.label.startswith('7E8'))
 def test_local_dtc_reference_and_invalid_selection(self):
  import time
  from unittest.mock import patch
  self.window.vehicle={'make':'Renault'}
  self.ui.rows(self.ui.dtc,[['7E8','stored','ok','P0100']]);self.ui.dtc.selectRow(0)
  with patch('automotive_data.dtc',return_value={'code':'P0100','definitions':[{'description':'Air flow circuit','source':'local fixture','applicability':'Verify ECU applicability'}]}) as lookup:
   self.ui.lookup_dtc()
   until=time.monotonic()+5
   while self.ui.worker is not None and time.monotonic()<until:self.app.processEvents();time.sleep(.01)
   lookup.assert_called_once_with('P0100','Renault');self.assertIn('Air flow circuit',self.ui.dtc_reference.toPlainText());self.assertIn('local fixture',self.ui.dtc_reference.toPlainText())
  with patch('automotive_data.dtc') as lookup:
   self.ui.rows(self.ui.dtc,[['7E8','stored','error','NO DATA']]);self.ui.dtc.selectRow(0);self.ui.lookup_dtc();self.ui.dtc.clearSelection();self.ui.lookup_dtc();lookup.assert_not_called();self.assertIsNone(self.ui.worker)
 def test_fresh_scan_archives_and_resets_old_recording(self):
  from unittest.mock import patch
  old={'id':'vehicle-A-session','vehicle':{'make':'A'},'evidence':'simulator','ecus':[{'id':'7E8','supported_pids':[12]}]};self.ui.display(old);self.ui.record.setChecked(True);self.ui.live_result([{'ecu':'7E8','pid':12,'value':1726}]);self.ui.dtc_reference.setPlainText('old definition');self.window.vehicle={'make':'B'}
  with patch('diagnostic_workspace.store.save') as save,patch.object(self.ui,'launch'):
   self.ui.scan();save.assert_called_once();self.assertEqual(save.call_args.args[2]['samples'][0]['session_id'],'vehicle-A-session');self.assertEqual(save.call_args.args[2]['samples'][0]['vehicle'],{'make':'A'});self.assertEqual(save.call_args.args[0],{'make':'A'});self.assertEqual(save.call_args.args[1],'OBD_LIVE_RECORDING');self.assertEqual(save.call_args.args[2]['session_id'],'vehicle-A-session')
  self.assertFalse(self.ui.samples);self.assertFalse(self.ui.recorded);self.assertFalse(self.ui.record.isChecked());self.assertEqual(self.ui.live_table.rowCount(),0);self.assertFalse(self.ui.graph.points);self.assertEqual(self.ui.dtc_reference.toPlainText(),'');self.assertIsNone(self.ui.report)
 def test_busy_scan_does_not_reset(self):
  from unittest.mock import patch
  self.ui.recorded=[{'value':123}];self.window._obd_worker=object()
  with patch('diagnostic_workspace.store.save') as save:self.ui.scan();save.assert_not_called()
  self.assertEqual(self.ui.recorded,[{'value':123}]);self.window._obd_worker=None
 def test_connection_generation_requires_scan(self):
  from unittest.mock import patch
  import transport
  self.ui.show();self.ui.live_on=True;self.ui.timer.start();generation=getattr(transport.LINK,'generation',0)
  with patch.object(transport.LINK,'generation',generation+1,create=True),patch.object(self.ui.session,'live') as live:
   self.ui.poll();live.assert_not_called();self.assertFalse(self.ui.timer.isActive());self.assertFalse(self.ui.live_on)
 def test_uncertain_clear_is_preserved_in_report(self):
  from unittest.mock import patch
  from PySide6.QtWidgets import QMessageBox
  result={'before':{'id':'before'},'after':{'id':'after','status':'complete','ecus':[],'errors':[]},'status':'partial','acknowledgements':['7E8'],'verification_scope':'Stored and pending emissions DTC readback only; permanent DTC not cleared','errors':[{'error':'Missing 7E9 acknowledgement'}],'trace':[{'command':'04','response':'44'}]}
  def launch(fn,done):done(result)
  with patch('diagnostic_workspace.QMessageBox.question',return_value=QMessageBox.Yes),patch.object(self.ui,'launch',side_effect=launch):self.ui.clear()
  self.assertEqual(self.ui.report['status'],'partial');self.assertIn('permanent DTC not cleared',self.ui.report['clear_action']['scope']);self.assertEqual(self.ui.report['clear_action']['before_id'],'before');self.assertIn('Missing 7E9 acknowledgement',self.ui.summary.toPlainText());self.assertEqual(self.ui.report['errors'][0]['section'],'clear-operation')
 def test_recorded_csv_export(self):
  import tempfile,csv,io
  from unittest.mock import patch
  self.ui.recorded=[{'ecu':'7E8','pid':12,'name':'RPM','value':1726,'unit':'rpm','at':'observed'}]
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'samples.csv'
   with patch('diagnostic_workspace.QFileDialog.getSaveFileName',return_value=(str(path),'CSV')):self.ui.export_live()
   rows=list(csv.DictReader(io.StringIO(path.read_text())));self.assertEqual(rows[0]['value'],'1726');self.assertEqual(rows[0]['ecu'],'7E8')
if __name__=='__main__':unittest.main()

@unittest.skipIf(Workspace is None,'Qt runtime not on Python path')
class SimulatorWorkspace(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
 def setUp(self):
  import transport
  from obd_simulator import Simulator
  self.transport=transport;self.previous=transport.LINK;self.sim=Simulator().start();self.link=transport.Link();self.link.connect('wifi',f'127.0.0.1:{self.sim.port}',family='elm');transport.LINK=self.link
  class Window(QWidget):
   vehicle={}
   def adapter_page(self):pass
  self.window=Window();self.ui=Workspace(self.window);self.window.show();self.ui.show()
 def wait(self):
  import time
  stop=time.monotonic()+20
  while self.ui.worker is not None and time.monotonic()<stop:self.app.processEvents();time.sleep(.01)
  self.assertIsNone(self.ui.worker)
 def tearDown(self):
  self.ui.stop();self.wait();self.ui.deleteLater();self.window.deleteLater();self.app.processEvents();self.link.close();self.sim.stop();self.transport.LINK=self.previous
 def test_real_scan_then_live(self):
  self.ui.scan();self.wait();self.assertEqual(self.ui.report['evidence'],'simulator');self.ui.pids.setCurrentIndex(self.ui.pids.findData(12));self.ui.poll();self.wait();self.assertTrue(self.ui.samples, self.ui.status.text());self.assertTrue(any(r.get('pid')==12 and isinstance(r.get('value'),(int,float)) for r in self.ui.samples));self.assertIn('SIMULATOR',self.ui.summary.toPlainText())
 def test_hidden_and_close_cancel_running_scan(self):
  import time
  original=self.sim.reply
  def delayed(command):
   time.sleep(.03);return original(command)
  self.sim.reply=delayed
  self.ui.scan();self.assertTrue(self.ui.worker.isRunning());self.assertFalse(self.window.close());self.ui.hide();self.assertFalse(self.ui.timer.isActive());self.wait();self.assertEqual(self.ui.report['status'],'cancelled');self.assertTrue(self.window.close())
 def test_page_deleted_during_scan(self):
  import time
  from shiboken6 import delete
  original=self.sim.reply
  def delayed(command):time.sleep(.03);return original(command)
  self.sim.reply=delayed;self.ui.scan();worker=self.ui.worker;delete(self.ui);worker.cancel.set()
  stop=time.monotonic()+20
  while getattr(self.window,'_obd_worker',None) is not None and time.monotonic()<stop:self.app.processEvents();time.sleep(.01)
  self.assertIsNone(getattr(self.window,'_obd_worker',None))
  self.ui=Workspace(self.window)
