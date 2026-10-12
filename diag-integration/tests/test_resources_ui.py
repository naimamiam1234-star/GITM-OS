import tempfile,json,unittest
from pathlib import Path
from unittest.mock import patch
from PySide6.QtWidgets import QApplication,QWidget
from PySide6.QtCore import QCoreApplication,QEvent
import resource_workspace as resources
APP=QApplication.instance() or QApplication([])
class ResourceTests(unittest.TestCase):
 def setUp(self):self.window=QWidget();self.pages=[]
 def tearDown(self):
  for page in self.pages:page.deleteLater()
  self.window.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)
 def page(self,rows):
  page=resources.SourcesWorkspace(self.window,rows=rows);self.pages.append(page);return page
 def test_flags_license_and_no_automatic_open(self):
  with patch('resource_workspace.QDesktopServices.openUrl') as opened:
   page=self.page([{'name':'Test','url':'https://example.org','status':'Partial','redistribution':'CHECK_LICENSE','integration_verified':False}]);opened.assert_not_called()
   self.assertEqual(page.table.item(0,2).text(),'CHECK_LICENSE');self.assertIn('Partial',page.details.toPlainText());self.assertFalse(page.verified_count.value_label.text().startswith('1'))
   page.open_selected();opened.assert_called_once()
 def test_filter_selection_and_url_reject(self):
  with patch('resource_workspace.QDesktopServices.openUrl') as opened:
   page=self.page([{'name':'Blocked','url':'file:///tmp/x','integration_verified':True},{'name':'Safe','url':'https://example.org','integration_verified':False}]);self.assertFalse(page.open_button.isEnabled());page.open_selected();opened.assert_not_called();page.search.setText('Safe');self.assertEqual(page.table.rowCount(),1);self.assertIn('Safe',page.details.toPlainText());self.assertTrue(page.open_button.isEnabled())
 def test_missing_flags_are_unknown_and_empty_is_useful(self):
  page=self.page([{'name':'Unknown'}]);self.assertIn('—',page.details.toPlainText());page.search.setText('Absent');self.assertFalse(page.open_button.isEnabled());self.assertTrue(page.empty.isVisibleTo(page))
 def test_catalog_reads_local_actual_schema(self):
  rows,error=resources.load_sources();self.assertFalse(error);self.assertGreater(len(rows),20);self.assertIn('redistribution',rows[0]);self.assertIs(rows[0]['integration_verified'],False)
 def test_invalid_catalog_empty_error(self):
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'sources.json';path.write_text('{}');rows,error=resources.load_sources(path);self.assertEqual(rows,[]);self.assertTrue(error)
 def test_recalls_capture_selection_only_on_explicit_action(self):
  with patch('source_gateway.recalls',return_value={}) as request:
   page=self.page([]);request.assert_not_called();page.recalls();request.assert_not_called()
   self.window.vehicle={'make':'A','model':'B','year':'2020'};captured=[];page.launch=lambda fn,done:captured.append(fn);page.recalls();self.window.vehicle={'make':'Other'};captured[0](None,None);request.assert_called_once_with('A','B','2020')
 def test_evidence_import_preserves_engine_license_validation(self):
  page=self.page([]);captured=[];page.launch=lambda fn,done:captured.append(fn)
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'evidence.json';path.write_text('{}')
   with patch('resource_workspace.QFileDialog.getOpenFileName',return_value=(str(path),'')):page.import_evidence()
   with self.assertRaisesRegex(ValueError,'Missing source'):captured[0](None,None)
 def test_wiring_reference_has_all_pins_no_observations(self):
  with patch('transport.LINK.query') as query:
   page=resources.WiringWorkspace(self.window);self.pages.append(page);query.assert_not_called()
  self.assertEqual(page.table.rowCount(),16);self.assertEqual(page.table.item(15,0).text(),'16');self.assertTrue(any(word in page.scope.text().lower() for word in ('reference','référence','مرجع')));self.assertIn('CAN H',page.table.item(5,1).text())


 def test_audit_counts_are_separate_from_catalog_claims(self):
  audit={'bundled_libraries':[{'license_inspected':True},{'license_inspected':True}], 'tested_integrations':[{'tested':True}]}
  page=resources.SourcesWorkspace(self.window,rows=[{'name':'Reference','integration_verified':False}],audit=audit);self.pages.append(page)
  self.assertEqual(page.license_count.value_label.text(),'2')
  self.assertEqual(page.software_count.value_label.text(),'1')
  self.assertEqual(page.verified_count.value_label.text(),'0')
 def test_audit_missing_is_not_positive_evidence(self):
  with tempfile.TemporaryDirectory() as directory:
   audit,error=resources.load_audit(Path(directory)/'missing.json');self.assertTrue(error);self.assertEqual(audit,{})
 def test_audit_manifest_hashes_and_scope(self):
  import hashlib
  audit=json.loads((Path(resources.__file__).parent/'source_audit.json').read_text());base=Path(resources.__file__).resolve().parents[2]
  self.assertEqual(audit['catalog']['record_count'],35)
  self.assertEqual(audit['catalog']['verified_integrations'],0)
  self.assertEqual(len(audit['bundled_libraries']),2)
  for evidence in audit['evidence']:
   self.assertEqual(hashlib.sha256((base/evidence['path']).read_bytes()).hexdigest(),evidence['sha256'])
  self.assertTrue(all(row['integration_verified'] is False for row in resources.load_sources()[0]))

 def test_odx_dependency_loading_is_real_and_offline(self):
  import odx_engine
  library=odx_engine.library()
  self.assertEqual(library.__version__,'11.6.2')
  self.assertTrue(callable(library.load_file))
  self.assertIn('odx-vendor',library.__file__)
