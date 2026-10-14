import unittest
from unittest.mock import patch
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QWidget, QStyleOptionButton, QStyle
import vehicle_workspace
from professional_components import styles

APP = QApplication.instance() or QApplication([])

class VehicleGeometryTests(unittest.TestCase):
 def test_brand_content_fits_real_theme_and_font_sizes(self):
  for dark in (False, True):
   for font_size in (16, 22):
    with self.subTest(dark=dark, font_size=font_size), patch('vehicle_workspace.store.cache', return_value=None):
     window = QWidget();window.vehicle = {}
     page = vehicle_workspace.Workspace(window, logos={'Mercedes-Benz': {}, 'BMW': {}})
     pix = QPixmap(64, 48);pix.fill(Qt.red)
     button = page.buttons['Mercedes-Benz'];button.setIcon(QIcon(pix))
     page.setStyleSheet(styles(dark, font_size));page.resize(1024, 900);page.show();APP.processEvents()
     button.resize(button.width(), button.minimumHeight())
     option = QStyleOptionButton();button.initStyleOption(option)
     content = button.style().subElementRect(QStyle.SE_PushButtonContents, option, button)
     self.assertGreaterEqual(content.height(), max(button.iconSize().height(), button.fontMetrics().height()))
     self.assertLessEqual(button.iconSize().width(), 76)
     self.assertGreaterEqual(button.height()-88, button.fontMetrics().height())
     self.assertEqual(button.objectName(), 'vehicleBrand')
     page.close();page.deleteLater();window.deleteLater();APP.processEvents()

 def test_click_keyboard_search_favorites_and_responsive_grid(self):
  with patch('vehicle_workspace.store.cache', return_value=None):
   window = QWidget();window.vehicle = {}
   page = vehicle_workspace.Workspace(window, logos={'BMW': {}, 'Toyota': {}, 'Volvo': {}})
   page.setStyleSheet(styles());page.resize(1024, 900);page.show();APP.processEvents()
   QTest.mouseClick(page.buttons['Toyota'], Qt.LeftButton)
   self.assertEqual(page.fields['make'].text(), 'Toyota')
   page.tabs.setCurrentIndex(0);APP.processEvents();page.buttons['BMW'].setFocus();QTest.keyClick(page.buttons['BMW'], Qt.Key_Space)
   self.assertEqual(page.fields['make'].text(), 'BMW')
   page.favorite();page.only_favorites.setChecked(True)
   self.assertEqual(page.grid.count(), 1)
   self.assertIs(page.grid.itemAt(0).widget(), page.buttons['BMW'])
   page.only_favorites.setChecked(False);page.search.setText('toy')
   self.assertEqual(page.grid.count(), 1)
   self.assertIs(page.grid.itemAt(0).widget(), page.buttons['Toyota'])
   page.search.clear();page.resize(1280, 900);APP.processEvents()
   self.assertEqual(page.columns(), 4)
   page.resize(700, 900);APP.processEvents();self.assertEqual(page.columns(), 2)
   page.close();page.deleteLater();window.deleteLater();APP.processEvents()

