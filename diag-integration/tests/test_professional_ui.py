import os,unittest,sys
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path.cwd()/'source/GearDiag-Raw-Build/app')]
from PySide6.QtWidgets import QApplication,QTableWidget
from PySide6.QtCore import Qt
app=QApplication.instance() or QApplication([])
class Components(unittest.TestCase):
 def module(self):
  try:import professional_components as c;return c
  except ImportError:self.fail('Shared professional components are missing')
 def test_missing_metric_has_no_fabricated_zero(self):
  c=self.module();card=c.MetricCard('Voltage');self.assertEqual(card.value_label.text(),'—');card.set_value('12.6 V','Measured');self.assertEqual(card.value_label.text(),'12.6 V');self.assertEqual(card.detail_label.text(),'Measured')
 def test_buttons_roles_and_table_no_edit(self):
  c=self.module();self.assertEqual(c.action_button('Clear','warning').property('role'),'warning');table=QTableWidget();c.configure_table(table);self.assertEqual(table.editTriggers(),QTableWidget.NoEditTriggers)
 def test_token_themes_have_opposite_surface_luminance(self):
  c=self.module();from PySide6.QtGui import QColor
  self.assertGreater(QColor(c.palette(False)['surface']).lightness(),QColor(c.palette(True)['surface']).lightness());self.assertIn('QPushButton:focus',c.styles(False,16))
class ReadabilityTests(unittest.TestCase):
 def test_rtl_selection_and_latin_cell_direction(self):
  from professional_components import configure_table
  from PySide6.QtWidgets import QTableWidgetItem,QStyleOptionViewItem
  previous=app.layoutDirection();self.addCleanup(app.setLayoutDirection,previous);app.setLayoutDirection(Qt.RightToLeft)
  table=QTableWidget(2,2);configure_table(table)
  for row in range(2):
   table.setItem(row,0,QTableWidgetItem('P0401'));table.setItem(row,1,QTableWidgetItem('عطل'))
  table.resize(500,200);table.show();self.addCleanup(table.close);app.processEvents();table.selectRow(0)
  self.assertEqual(len(table.selectedItems()),2)
  table.selectRow(-1);self.assertEqual(len(table.selectedItems()),2)
  table.selectRow(table.rowCount());self.assertEqual(len(table.selectedItems()),2)
  from PySide6.QtTest import QTest
  table.clearSelection()
  QTest.mouseClick(table.viewport(),Qt.LeftButton,Qt.NoModifier,table.visualItemRect(table.item(0,0)).center())
  self.assertEqual({(item.row(),item.column()) for item in table.selectedItems()},{(0,0),(0,1)})
  QTest.keyClick(table,Qt.Key_Down)
  self.assertEqual({(item.row(),item.column()) for item in table.selectedItems()},{(1,0),(1,1)})
  for column,direction in ((0,Qt.LeftToRight),(1,Qt.RightToLeft)):
   option=QStyleOptionViewItem();table.itemDelegate().initStyleOption(option,table.model().index(0,column));self.assertEqual(option.direction,direction)
 def test_table_rows_follow_font_growth(self):
  from professional_components import configure_table
  table=QTableWidget(1,2);configure_table(table);before=table.rowHeight(0);font=table.font();font.setPixelSize(30);table.setFont(font);app.processEvents()
  self.assertGreater(table.rowHeight(0),before);self.assertGreaterEqual(table.rowHeight(0),table.fontMetrics().height()+16)
 def test_missing_multimedia_reports_backend_unavailable(self):
  from unittest.mock import patch
  from system_services import ServiceWindow
  from PySide6.QtWidgets import QLabel
  with patch.dict(sys.modules,{'PySide6.QtMultimedia':None}):
   window=ServiceWindow('camera');self.addCleanup(window.close);text=' '.join(label.text() for label in window.findChildren(QLabel));self.assertIn('QtMultimedia',text);self.assertNotIn('No connected camera',text);window.close()

if __name__=='__main__':unittest.main()

class ShellTests(unittest.TestCase):
 def shell(self):
  import native
  try:import professional_ui
  except ImportError:self.fail('Professional shell is missing')
  w=native.Window();professional_ui.install(w);self.addCleanup(w.close);return w,w.professional_shell
 def test_dashboard_and_navigation_keep_single_cached_page(self):
  w,s=self.shell();s.navigate('diagnosis');first=w.pages.currentWidget();s.navigate('reports');s.navigate('diagnosis');self.assertIs(w.pages.currentWidget(),first);self.assertEqual(len(w.home_cards),20)
 def test_unknown_footer_measurement_and_split_actions(self):
  w,s=self.shell();s.refresh();self.assertNotIn('12.6',s.context.text());self.assertEqual(w.menuBar().actions(),[]);self.assertGreaterEqual(len(s.split.menu().actions()),2)
 def test_close_cancels_cloud_task_without_destroying_running_thread(self):
  import threading
  from PySide6.QtCore import QThread,QEvent
  class Pending(QThread):
   def isRunning(self):return True
  w,s=self.shell();w.task=Pending(w);w.ai_cancel=threading.Event();event=QEvent(QEvent.Close)
  self.assertTrue(w.close_guard.eventFilter(w,event));self.assertTrue(w.ai_cancel.is_set());self.assertFalse(event.isAccepted());w.task=None
 def test_page_callbacks_use_navigation_cache(self):
  w,s=self.shell();s.navigate('diagnosis');diagnosis=w.pages.currentWidget()
  w.adapter_page();adapter=w.pages.currentWidget();count=w.pages.count()
  for _ in range(3):
   w.diagnosis_page();self.assertIs(w.pages.currentWidget(),diagnosis)
   w.adapter_page();self.assertIs(w.pages.currentWidget(),adapter)
  self.assertEqual(w.pages.count(),count);self.assertIs(s.cache['adapter'],adapter)
 def test_cached_vehicle_forms_follow_external_context_without_losing_drafts(self):
  w,s=self.shell();w.vehicle={'make':'A','model':'First','year':2020,'engine':'One','vin':'VIN-A'}
  for key in ('vehicle','ecu'):
   s.navigate(key);page=w.pages.currentWidget();ui=next(child for child in page.findChildren(__import__('PySide6.QtWidgets',fromlist=['QWidget']).QWidget) if hasattr(child,'fields'))
   ui.fields['model'].setText('Unsaved draft');s.home();s.navigate(key)
   self.assertEqual(ui.fields['model'].text(),'Unsaved draft')
   s.home();w.vehicle={'make':'B','model':'Second','year':2022,'engine':'Two','vin':'VIN-B'};s.navigate(key)
   for field in ui.fields:self.assertEqual(ui.fields[field].text(),str(w.vehicle[field]))
   w.vehicle={'make':'A','model':'First','year':2020,'engine':'One','vin':'VIN-A'}
 def test_font_choices_preserve_other_preferences(self):
  from unittest.mock import patch
  import system_settings
  prefs={'theme':'light','font_size':16,'motion':'reduced','custom':'kept'}
  with patch.object(system_settings,'preferences',return_value=prefs),patch.object(system_settings,'save_preferences') as save:
   w,s=self.shell();self.assertEqual([a.text() for a in s.font_menu.actions()],['16 px','18 px','20 px'])
   s.set_font_size(20);self.assertEqual(save.call_args.args[0],{**prefs,'font_size':20});self.assertIn('font-size:20px',w.styleSheet())
 def test_four_geometry_targets_have_no_horizontal_overflow(self):
  w,s=self.shell()
  for width,height in ((1024,768),(1280,800),(1366,768),(1920,1080)):
   w.resize(width,height);w.show();app.processEvents();self.assertLessEqual(w.width(),width);self.assertLessEqual(w.minimumSizeHint().height(),height)
