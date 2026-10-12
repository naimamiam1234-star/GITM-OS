import unittest
import copy
from workshop_workspace import filter_records, compare_reports
from ai_workspace import sanitized_scan

class WorkshopTests(unittest.TestCase):
 def test_filter_real_identity(self):
  rows=[{'id':7,'command':'OBD_SESSION','vehicle':{'make':'Ford'},'result':{'evidence':'simulator'}},{'id':8,'command':'OTHER','vehicle':{},'result':{}}]
  assert filter_records(rows,'ford','simulator')==[rows[0]]
  assert filter_records(rows,'missing','all')==[]
 
 def test_comparison_unknown_not_clean(self):
  a={'format':'gitm-obd-session/1','evidence':'physical','ecus':[{'id':'7E8','dtc':{'stored':{'status':'ok','codes':['P0100']}}}]}
  b={'format':'gitm-obd-session/1','evidence':'physical','ecus':[]}
  with patch('professional_components.language',return_value='en'):assert 'unknown' in compare_reports(a,b).lower()
  b['evidence']='simulator'
  with patch('professional_components.language',return_value='en'):assert 'simulator' in compare_reports(a,b).lower()
 
 def test_scan_redaction_preserves_original(self):
  original={'vehicle':{'VIN':'ABC','client':'Jane','make':'Ford'},'ecus':[{'vin':'ABC','dtc':{}}],'trace':[{'response':'ABC'}],'errors':[{'section':'VIN','error':'ABC acquisition failed for Jane'}]}
  before=copy.deepcopy(original); result=sanitized_scan(original)
  assert 'ABC' not in str(result) and 'Jane' not in str(result)
  assert result['vehicle']['make']=='Ford' and original==before
  assert 'acquisition failed' in result['errors'][0]['error']

from unittest.mock import patch
import tempfile,time
from pathlib import Path
from PySide6.QtWidgets import QApplication,QWidget,QLineEdit
from workshop_workspace import History
from ai_workspace import Assistant
from update_workspace import Updates

class WorkshopQtTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
 def setUp(self):
  self.window=QWidget();self.window.task=None;self.window.vehicle={};self.widgets=[]
 def tearDown(self):
  for widget in self.widgets:widget.deleteLater()
  self.window.deleteLater();self.app.processEvents()
 def test_sqlite_selection_is_real_and_filters(self):
  import store
  with tempfile.TemporaryDirectory() as directory,patch.object(store,'BASE',Path(directory)):
   store.save({'make':'Ford'},'OBD_SESSION',{'format':'gitm-obd-session/1','evidence':'simulator','ecus':[]})
   ui=History(self.window);self.widgets.append(ui);self.assertEqual(ui.table.rowCount(),1);ui.table.selectRow(0)
   self.assertEqual(ui.selection()[0]['id'],1);self.assertIn('SIMULATOR',ui.preview.toPlainText());self.assertTrue(ui.exports[0].isEnabled())
   ui.search.setText('absent');self.assertEqual(ui.table.rowCount(),0);self.assertFalse(ui.exports[0].isEnabled())
 def test_preview_and_send_require_consent_without_network(self):
  with patch('cloud_ai.stream_chat') as cloud:
   ui=Assistant(self.window);self.widgets.append(ui);self.assertEqual(ui.key.echoMode(),QLineEdit.Password)
   with patch('ai_workspace.current_scan',return_value={'vehicle':{'vin':'VINSECRET','client':'Jane'},'evidence':'simulator','ecus':[]}):ui.attach()
   self.assertNotIn('VINSECRET',ui.preview.toPlainText());self.assertNotIn('Jane',ui.preview.toPlainText());self.assertFalse(ui.approve.isChecked());ui.send();cloud.assert_not_called()
   ui.key.setText('SESSIONSECRET');self.assertEqual(self.window.openrouter_key,'SESSIONSECRET')
 def test_invalid_signature_disables_install(self):
  with patch('usb_update.release',return_value={'version':'test'}),patch('update_workspace.inspect_package',side_effect=ValueError('invalid signature')):
   ui=Updates(self.window)
   self.widgets.append(ui)
   ui.verify('/tmp/invalid.gitmupdate')
   deadline=time.monotonic()+2
   while ui.worker is not None and time.monotonic()<deadline:self.app.processEvents();time.sleep(.005)
   self.assertIsNone(ui.worker);self.assertFalse(ui.install.isEnabled());self.assertIsNone(ui.selected_path);self.assertIn('invalid signature',ui.raw.toPlainText())
