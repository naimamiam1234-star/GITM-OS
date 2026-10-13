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
 def test_brand_opens_a_new_model_page_and_only_catalog_years_follow(self):
  row={'make':'Test','model':'Synthetic model','generation':'A','market':'Test fixture','source':'Synthetic fixture','years':[2024,2026],'engines':[{'name':'Fixture engine','fuel':'Diesel','source':'Synthetic fixture','years':[2026]}]}
  self.page.catalog=[row];self.page.choose_make('Test');self.assertEqual(self.page.tabs.currentIndex(),1)
  self.page.choose_model(row);self.assertEqual(self.page.tabs.currentIndex(),2)
  self.page.choose_year(2026);self.assertEqual(self.page.tabs.currentIndex(),3)
  self.page.choose_engine(row['engines'][0]);self.assertEqual(self.page.tabs.currentIndex(),4);self.assertEqual(self.page.fields['fuel'].text(),'Diesel')
 def test_brand_page_has_no_review_actions(self):
  self.assertEqual(self.page.tabs.currentIndex(),0);self.assertTrue(self.page.back.isHidden());self.assertTrue(all(button.isHidden() for button in self.page.actions));self.assertTrue(self.page.scope.isHidden())
  self.page.choose_make('RENAULT');self.assertEqual(self.page.tabs.currentIndex(),1);self.assertTrue(all(button.isHidden() for button in self.page.actions))
 def test_save_disabled_until_review(self):
  self.assertFalse(self.page.actions[0].isEnabled());self.page.tabs.setCurrentIndex(4);self.assertTrue(self.page.actions[0].isEnabled())
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
