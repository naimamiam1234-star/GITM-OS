import unittest,sys,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
try:
 from PySide6.QtWidgets import QApplication,QWidget
 from diagnostic_workspace import Workspace, Graph
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
 def test_vehicle_context_change_cannot_relabel_or_continue_old_session(self):
  from unittest.mock import patch
  self.window.vehicle={'make':'Original'};self.ui.display({'vehicle':{'make':'Original'},'status':'complete','ecus':[{'id':'7E8','supported_pids':[12]}]})
  self.window.vehicle={'make':'New selection'};self.ui.refresh_connection()
  self.assertIn('Original',self.ui.connection.text());self.assertNotIn('New selection',self.ui.connection.text())
  with patch.object(self.ui,'launch') as request:self.ui.toggle_live();request.assert_not_called()
  self.assertFalse(self.ui.live_on)
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
  with patch('diagnostic_workspace.QMessageBox.question',return_value=QMessageBox.Yes),patch.object(self.ui,'launch',side_effect=launch),patch.object(self.ui,'update_actions'):
   self.ui.clear_button.setEnabled(True);self.ui.clear()
  self.assertEqual(self.ui.report['status'],'partial');self.assertIn('permanent DTC not cleared',self.ui.report['clear_action']['scope']);self.assertEqual(self.ui.report['clear_action']['before_id'],'before');self.assertIn('Missing 7E9 acknowledgement',self.ui.summary.toPlainText());self.assertEqual(self.ui.report['errors'][0]['section'],'clear-operation')
 def test_localized_acquisition_readiness_and_readable_times(self):
  from unittest.mock import patch
  report={'status':'complete','started_at':'2026-10-11T12:34:56.123456+00:00','adapter':{'connected':True,'adapter':'elm','target':'127.0.0.1:35000'},'ecus':[{'id':'7E8','supported_pids':[12],'dtc':{'stored':{'status':'ok','codes':['P0100']}},'readiness':{'MIL':False,'monitors':[{'name':'Catalyst','supported':False,'complete':None}]}}]}
  with patch('diagnostic_workspace.language',return_value='ar'):
   self.ui.display(report);self.assertEqual(self.ui.dtc.item(0,1).text(),'مخزن');self.assertEqual(self.ui.dtc.item(0,2).text(),'قراءة ناجحة');self.assertEqual(self.ui.ready.item(0,1).text(),'لا');self.assertEqual(self.ui.ready.item(0,5).text(),'غير مدعوم')
   self.ui.live_result([{'ecu':'7E8','pid':12,'value':1000,'at':'2026-10-11T12:34:56.123456+00:00'}]);self.assertEqual(self.ui.live_table.item(0,0).text(),'12:34:56 UTC');self.assertEqual(self.ui.samples[-1]['at'],'2026-10-11T12:34:56.123456+00:00')
  summary=self.ui.summary.toPlainText();self.assertNotIn('True',summary);self.assertIn('2026-10-11 12:34:56 UTC',summary)
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

@unittest.skipIf(Workspace is None,'Qt runtime not on Python path')
class ProfessionalWorkspaceTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
 setUp=WorkspaceTests.setUp
 tearDown=WorkspaceTests.tearDown
 def test_empty_actions_and_unknown_metrics(self):
  self.assertFalse(self.ui.export_button.isEnabled());self.assertFalse(self.ui.clear_button.isEnabled());self.assertTrue(self.ui.cancel_button.isHidden())
  self.assertEqual(self.ui.metrics['dtc'].value_label.text(),'—');self.assertEqual(self.ui.metrics['mil'].value_label.text(),'—')
 def test_partial_results_keep_unknown_counts_and_filter_raw_evidence(self):
  report={'status':'partial','evidence':'simulator','ecus':[{'id':'7E8','dtc':{'stored':{'status':'ok','codes':['P0100']},'pending':{'status':'error','error':'NO DATA','codes':[]}}}]}
  self.ui.display(report);self.assertEqual(self.ui.metrics['dtc'].value_label.text(),'—');self.assertTrue(self.ui.export_button.isEnabled());self.assertFalse(self.ui.clear_button.isEnabled())
  self.ui.dtc_search.setText('P0100');self.assertFalse(self.ui.dtc.isRowHidden(0));self.assertTrue(self.ui.dtc.isRowHidden(1));self.assertIs(self.ui.report,report);self.assertFalse(self.ui.simulator_badge.isHidden())
 def test_clear_requires_current_complete_connected_scan(self):
  from unittest.mock import patch
  import transport
  with patch.object(transport.LINK,'info',return_value={'connected':True}):
   self.ui.connection_identity=self.ui.connection_key();self.ui.display({'status':'complete','ecus':[{'id':'7E8','dtc':{'stored':{'status':'ok','codes':[]}}}]})
   self.assertTrue(self.ui.clear_button.isEnabled())
   with patch.object(transport.LINK,'generation',getattr(transport.LINK,'generation',0)+1,create=True):self.ui.refresh_connection();self.assertFalse(self.ui.clear_button.isEnabled())

 def test_running_action_state_and_completion(self):
  import time
  def operation(cancel,progress):
   progress('Responder discovery')
   cancel.wait(2)
   return {'status':'cancelled','ecus':[]}
  self.ui.launch(operation,self.ui.display)
  self.assertFalse(self.ui.cancel_button.isHidden());self.assertFalse(self.ui.progress.isHidden());self.assertEqual(self.ui.progress.maximum(),0);self.assertFalse(self.ui.export_button.isEnabled())
  self.ui.stop();until=time.monotonic()+5
  while self.ui.worker is not None and time.monotonic()<until:self.app.processEvents();time.sleep(.01)
  self.assertIsNone(self.ui.worker);self.assertTrue(self.ui.cancel_button.isHidden());self.assertTrue(self.ui.progress.isHidden());self.assertTrue(self.ui.export_button.isEnabled());self.assertFalse(self.ui.clear_button.isEnabled())

 def test_changed_vehicle_cannot_clear_cached_report(self):
  from unittest.mock import patch
  import transport
  self.window.vehicle={'make':'Renault','model':'Clio','year':2022}
  with patch.object(transport.LINK,'info',return_value={'connected':True}):
   self.ui.connection_identity=self.ui.connection_key();self.ui.display({'status':'complete','vehicle':dict(self.window.vehicle),'ecus':[{'id':'7E8','dtc':{'stored':{'status':'ok','codes':[]}}}]})
   self.assertTrue(self.ui.clear_button.isEnabled())
   self.window.vehicle={'make':'Renault','model':'Megane','year':2022};self.ui.refresh_connection()
   self.assertFalse(self.ui.clear_button.isEnabled());self.assertTrue(self.ui.export_button.isEnabled())
   with patch('diagnostic_workspace.QMessageBox.question') as confirmation:self.ui.clear();confirmation.assert_not_called()
 def test_graph_real_time_and_statistics_do_not_blend_ecus(self):
  self.ui.display({'status':'complete','ecus':[{'id':'7E8','supported_pids':[5,12]},{'id':'7E9','supported_pids':[12]}]})
  self.ui.pids.setCurrentIndex(self.ui.pids.findData(12));self.ui.set_pid_selected(5,True)
  self.ui.live_result([{'ecu':'7E8','pid':12,'value':1000,'unit':'rpm','at':'2026-10-12T12:00:00Z'},{'ecu':'7E9','pid':12,'value':9000,'unit':'rpm','at':'2026-10-12T12:00:01Z'},{'ecu':'7E8','pid':12,'value':2000,'unit':'rpm','at':'2026-10-12T12:00:05Z'},{'ecu':'7E8','pid':5,'value':85,'unit':'°C','at':'2026-10-12T12:00:05Z'}])
  self.assertEqual(self.ui.graph.series[12]['elapsed'],[0.0,5.0]);self.assertEqual(self.ui.graph.series[12]['mean'],1500);self.assertEqual(self.ui.graph.series[12]['max'],2000);self.assertEqual(self.ui.graph.series[5]['unit'],'°C')
  self.ui.pause_graph.setChecked(True);self.ui.record.setChecked(True);self.ui.live_result([{'ecu':'7E8','pid':12,'value':3000,'at':'2026-10-12T12:00:09Z'}]);self.assertEqual(self.ui.graph.series[12]['max'],2000);self.assertEqual(self.ui.recorded[-1]['value'],3000)
  self.ui.pause_graph.setChecked(False);self.assertEqual(self.ui.graph.series[12]['max'],3000)
 def test_multi_pid_selection_is_bounded_and_missing_clock_is_unknown(self):
  self.ui.display({'status':'complete','ecus':[{'id':'7E8','supported_pids':[5,12,13,15,17,20]}]})
  for pid in (5,12,13,15,17,20):self.ui.set_pid_selected(pid,True)
  self.assertLessEqual(len(self.ui.selected_pids()),5)
  self.ui.pids.setCurrentIndex(self.ui.pids.findData(12));self.ui.live_result([{'ecu':'7E8','pid':12,'value':1000}]);self.assertIsNone(self.ui.graph.series[12]['elapsed'][0])

 def test_worker_archives_captured_vehicle_after_selection_changes(self):
  import threading,time
  from unittest.mock import patch
  started=threading.Event();release=threading.Event();self.window.vehicle={'make':'A'}
  def scan(vehicle,cancel,progress):
   started.set();release.wait(3);return {'status':'complete','vehicle':vehicle,'ecus':[]}
  with patch.object(self.ui.session,'scan',side_effect=scan),patch('diagnostic_workspace.store.save') as save:
   self.ui.scan();self.assertTrue(started.wait(2));self.window.vehicle={'make':'B'};release.set();until=time.monotonic()+5
   while self.ui.worker is not None and time.monotonic()<until:self.app.processEvents();time.sleep(.01)
   self.assertIsNone(self.ui.worker);self.assertEqual(save.call_args.args[0],{'make':'A'});self.assertEqual(self.ui.report['vehicle'],{'make':'A'});self.assertFalse(self.ui.clear_button.isEnabled())
 def test_readiness_states_and_freeze_values_are_observed(self):
  self.ui.display({'status':'partial','ecus':[{'id':'7E8','readiness':{'monitors':[{'name':'A','supported':True,'complete':True},{'name':'B','supported':True,'complete':False},{'name':'C','supported':False,'complete':None},{'name':'D','supported':True,'complete':None}]},'freeze':{'values':[{'pid':12,'value':1726,'unit':'rpm'},{'pid':5,'value':85,'unit':'°C'}]}}]})
  for key in ('complete','incomplete','unsupported','unknown'):self.assertEqual(self.ui.readiness_cards[key].value_label.text(),'1')
  self.assertIn('1726',self.ui.freeze_cards[12].value_label.text());self.assertIn('7E8',self.ui.freeze_cards[12].detail_label.text());self.assertEqual(self.ui.freeze_cards[13].value_label.text(),'—')
 def test_split_view_reuses_session_and_samples_without_acquisition(self):
  from unittest.mock import patch
  self.ui.display({'status':'complete','ecus':[{'id':'7E8','supported_pids':[12],'dtc':{'stored':{'status':'ok','codes':['P0100']}}}]})
  session=self.ui.session
  with patch.object(session,'live') as live:self.ui.show_split();live.assert_not_called()
  self.assertIs(self.ui.session,session);self.assertEqual(self.ui.tabs.currentIndex(),6);self.assertEqual(self.ui.split_dtc.item(0,3).text(),'P0100')
  self.ui.live_result([{'ecu':'7E8','pid':12,'value':1726,'at':'2026-10-12T12:00:00Z'}]);self.assertEqual(list(self.ui.split_graph.points),[1726]);self.assertEqual(self.ui.split_live.item(0,4).text(),'1726')

@unittest.skipIf(Workspace is None,'Qt runtime not on Python path')
class GraphScaleTests(unittest.TestCase):
 def test_constant_and_variable_ranges_have_padding_and_five_ticks(self):
  for values in ([1726,1726],[0,0],[-10,-10],[1000,2000]):
   lo,hi=Graph.padded_range(values);ticks=Graph.graduations(lo,hi)
   self.assertLess(lo,min(values));self.assertGreater(hi,max(values));self.assertEqual(len(ticks),5)
   self.assertEqual(ticks[0],lo);self.assertEqual(ticks[-1],hi)
 def test_elapsed_ticks_preserve_irregular_acquisition_times(self):
  self.assertEqual(Graph.graduations(0,9),[0,2.25,4.5,6.75,9])

@unittest.skipIf(Workspace is None,'Qt runtime not on Python path')
class GraphLayoutTests(unittest.TestCase):
 setUpClass=classmethod(WorkspaceTests.setUpClass.__func__)
 setUp=WorkspaceTests.setUp
 tearDown=WorkspaceTests.tearDown
 def test_live_table_and_scroll_bounds(self):
  self.assertGreaterEqual(self.ui.live_table.minimumHeight(),140)
  self.assertLessEqual(self.ui.graph.parentWidget().parentWidget().maximumHeight(),280)
  self.ui.show_split();self.assertGreaterEqual(self.ui.split_live.minimumHeight(),140)
  self.assertLessEqual(self.ui.split_graph.parentWidget().parentWidget().maximumHeight(),280)
