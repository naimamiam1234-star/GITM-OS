import unittest
import copy,json
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
from PySide6.QtWidgets import QApplication,QWidget,QLineEdit,QFileDialog
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

class AnnotationTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
 def test_notes_preserve_original_and_local_permissions(self):
  import store
  from workshop_workspace import save_annotation,load_annotation,record_html,annotation_directory
  with tempfile.TemporaryDirectory() as directory,patch.object(store,'BASE',Path(directory)),patch('cloud_ai.stream_chat') as cloud:
   original={'format':'gitm-obd-session/1','evidence':'simulator','ecus':[]};store.save({},'OBD_SESSION',original);before=store.reports()[0]
   save_annotation(1,'<b>Technician observation</b>');self.assertEqual(load_annotation(1)['notes'],'<b>Technician observation</b>');self.assertEqual(store.reports()[0],before);cloud.assert_not_called()
   self.assertEqual(annotation_directory(1).stat().st_mode&0o777,0o700);self.assertEqual((annotation_directory(1)/'metadata.json').stat().st_mode&0o777,0o600);self.assertIn('&lt;b&gt;Technician',record_html(before))
 def test_image_validation_and_private_copy(self):
  from workshop_workspace import attach_image,load_annotation,annotation_directory,record_html,MAX_IMAGE_BYTES
  from PySide6.QtGui import QImage
  import store
  with tempfile.TemporaryDirectory() as directory,patch.object(store,'BASE',Path(directory)):
   bad=Path(directory)/'bad.svg';bad.write_text('<svg/>')
   with self.assertRaises(ValueError):attach_image(1,bad)
   large=Path(directory)/'large.png'
   with large.open('wb') as f:f.truncate(MAX_IMAGE_BYTES+1)
   with self.assertRaises(ValueError):attach_image(1,large)
   dimension=QImage(4097,1,QImage.Format_RGB32);dimension.fill(0);wide=Path(directory)/'wide.png';self.assertTrue(dimension.save(str(wide)))
   with self.assertRaises(ValueError):attach_image(1,wide)
   image=QImage(20,20,QImage.Format_RGB32);image.fill(0xff007700);path=Path(directory)/'valid.png';self.assertTrue(image.save(str(path)));attach_image(1,path)
   metadata=load_annotation(1);saved=annotation_directory(1)/metadata['image'];self.assertEqual(saved.stat().st_mode&0o777,0o600);self.assertIn('data:image/png;base64,',record_html({'id':1,'result':{}}))
 def test_no_selection_disables_annotations(self):
  import store
  with tempfile.TemporaryDirectory() as directory,patch.object(store,'BASE',Path(directory)):
   window=QWidget();ui=History(window);self.assertFalse(ui.save_notes.isEnabled());self.assertFalse(ui.add_image.isEnabled());self.assertFalse(ui.remove_image.isEnabled());ui.deleteLater();window.deleteLater();self.app.processEvents()

 def test_selected_html_json_exports_keep_original_record(self):
  import store
  from workshop_workspace import save_annotation
  with tempfile.TemporaryDirectory() as directory,patch.object(store,'BASE',Path(directory)):
   store.save({},'OBD_SESSION',{'format':'gitm-obd-session/1','ecus':[]});before=store.reports()[0];save_annotation(1,'Technician added note');window=QWidget();ui=History(window);ui.table.selectRow(0)
   for kind in ('HTML','JSON'):
    path=Path(directory)/('export.'+kind.lower())
    with patch.object(QFileDialog,'getSaveFileName',return_value=(str(path),'')):ui.export(kind)
    self.assertIn('Technician added note',path.read_text())
    if kind=='JSON':self.assertEqual(json.loads(path.read_text())['result'],before['result'])
   self.assertEqual(store.reports()[0],before);ui.deleteLater();window.deleteLater();self.app.processEvents()
