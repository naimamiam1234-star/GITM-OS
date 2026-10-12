import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from PySide6.QtWidgets import QApplication,QWidget
from PySide6.QtGui import QPixmap,QColor
import vehicle_workspace as v
APP=QApplication.instance() or QApplication([])
class IdentityCardTests(unittest.TestCase):
 def setUp(self):
  self.window=QWidget();self.window.vehicle={}
  with patch('vehicle_workspace.store.cache',return_value=None):self.page=v.Workspace(self.window,logos={})
 def tearDown(self):self.page.close();self.page.deleteLater();self.window.deleteLater();APP.processEvents()
 def test_manual_unknown_model_and_fuel_remain_editable(self):
  self.page.fields['model'].setText('Private model');self.page.fields['fuel'].setText('Hydrogen');self.assertEqual(self.page.fields['model'].text(),'Private model')
  with patch('vehicle_workspace.store.cache'):self.page.save_selection()
  self.assertEqual(self.window.vehicle['fuel'],'Hydrogen')
 def test_photo_clears_when_identity_changes(self):
  with tempfile.TemporaryDirectory() as directory:
   p=Path(directory)/'photo.png';im=QPixmap(100,60);im.fill(QColor('red'));im.save(str(p))
   self.page.photo_path=str(p);self.page.photo_identity=self.page.identity();self.page.refresh_state()
   self.assertFalse(self.page.photo.pixmap().isNull())
   self.page.fields['model'].setText('Different model')
   self.assertTrue(self.page.photo.pixmap().isNull())
 def test_stale_vin_result_does_not_replace_manual_values(self):
  self.page.fields['vin'].setText('1HGCM82633A004352');self.page.fields['model'].setText('Manual')
  self.page.display_vin('OTHER',{'vehicle':{'Make':'HONDA','Model':'Accord'}})
  self.assertEqual(self.page.fields['model'].text(),'Manual')
