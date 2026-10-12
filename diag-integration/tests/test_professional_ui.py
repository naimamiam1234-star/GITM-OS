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
 def test_four_geometry_targets_have_no_horizontal_overflow(self):
  w,s=self.shell()
  for width,height in ((1024,768),(1280,800),(1366,768),(1920,1080)):
   w.resize(width,height);w.show();app.processEvents();self.assertLessEqual(w.width(),width);self.assertLessEqual(w.minimumSizeHint().height(),height)
