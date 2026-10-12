import unittest,threading,time
from unittest.mock import patch, Mock
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import QSize,QCoreApplication,QEvent
import vci_workspace, vehicle_workspace
APP=QApplication.instance() or QApplication([])
class ConnectionVehicleTests(unittest.TestCase):
 def setUp(self):
  self.window=QWidget();self.window.vehicle={};self.widgets=[]
 def tearDown(self):
  for widget in self.widgets:widget.deleteLater()
  self.window.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete);APP.processEvents()
 def test_inventory_is_passive(self):
  with patch('vci_workspace.transport.inventory',return_value={'devices':[]}) as inventory,patch.object(vci_workspace.transport.LINK,'query') as query,patch.object(vci_workspace.transport.LINK,'connect') as connect:
   page=vci_workspace.Workspace(self.window);self.widgets.append(page);page.launch=lambda fn,done:done(fn(Mock(),Mock()));page.refresh_inventory();inventory.assert_called_once();query.assert_not_called();connect.assert_not_called()
 def test_disconnected_identity_has_no_fabricated_readings(self):
  with patch.object(vci_workspace.transport.LINK,'info',return_value={'connected':False}):
   page=vci_workspace.Workspace(self.window);self.widgets.append(page)
  self.assertEqual(page.identity.value_label.text(),'—');self.assertEqual(page.identity.detail_label.text(),'—')
 def test_shared_worker_blocks_adapter_launch(self):
  page=vci_workspace.Workspace(self.window);self.widgets.append(page);self.window._obd_worker=object()
  with patch('vci_workspace.Worker') as worker:page.connect_adapter();worker.assert_not_called()
 def test_worker_remains_serialized_until_cancelled_job_finishes(self):
  page=vci_workspace.Workspace(self.window);self.widgets.append(page);release=threading.Event();started=threading.Event();done=Mock()
  def operation(cancel,progress):
   started.set();release.wait(2);return {'connected':False}
  page.launch(operation,done)
  try:
   self.assertTrue(started.wait(1));worker=page.worker;worker.cancel.set()
   self.assertIs(self.window._obd_worker,worker);self.assertIs(worker.parent(),self.window)
  finally:
   release.set();deadline=time.monotonic()+2
   while page.worker is not None and time.monotonic()<deadline:APP.processEvents();time.sleep(.005)
  self.assertIsNone(self.window._obd_worker);done.assert_not_called()
 def test_connect_captures_values_before_worker(self):
  page=vci_workspace.Workspace(self.window);self.widgets.append(page);page.target.setText('/dev/ttyUSB7');captured=[];page.launch=lambda fn,done:captured.append(fn)
  page.connect_adapter();page.target.setText('/dev/ttyUSB9')
  with patch.object(vci_workspace.transport.LINK,'connect',return_value={}) as connect:
   captured[0](Mock(),Mock());self.assertEqual(connect.call_args.args,('usb','/dev/ttyUSB7',115200,'auto'))
 def test_selection_includes_year_engine(self):
  page=vehicle_workspace.Workspace(self.window,logos={});self.widgets.append(page);page.fields['make'].setText('Test');page.fields['year'].setText('2020');page.fields['engine'].setText('1.6')
  with patch('vehicle_workspace.store.cache'):page.save_selection()
  self.assertEqual(self.window.vehicle['year'],'2020');self.assertEqual(self.window.vehicle['engine'],'1.6')
 def test_grid_reflows_and_logo_bounds(self):
  page=vehicle_workspace.Workspace(self.window,logos={'A':{},'B':{},'C':{},'D':{},'E':{}});self.widgets.append(page);page.resize(1280,800);page.reflow();self.assertEqual(page.columns(),4)
  page.search.setText('E');self.assertEqual(page.grid.itemAtPosition(0,0).widget().text(),'E')
  self.assertEqual(page.buttons['E'].iconSize(),QSize(32,24));self.assertEqual(page.columns_for(1024),3)
 def test_lookup_requires_explicit_consent(self):
  page=vehicle_workspace.Workspace(self.window,logos={});self.widgets.append(page);page.launch=Mock();page.lookup();page.launch.assert_not_called()
if __name__=='__main__':unittest.main()
