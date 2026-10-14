import unittest
from PySide6.QtWidgets import QApplication
import native
app=QApplication.instance() or QApplication([])
class CockpitTests(unittest.TestCase):
 def test_mismatched_report_cannot_show_other_vehicle_units(self):
  w=native.Window();self.addCleanup(w.close);c=w.professional_shell.cockpit
  car=dict(make='Renault',model='Clio',year=2020)
  c.update_session(car,{'connected':True},{'vehicle':car,'ecus':[{'id':'7E8'}]})
  self.assertEqual(c.grid.count(),1)
  c.update_session(dict(car,model='Megane'),{'connected':True},{'vehicle':car,'ecus':[{'id':'7E8'}]})
  self.assertEqual(c.grid.count(),0)
 def test_no_connection_has_no_invented_units(self):
  w=native.Window();self.addCleanup(w.close);c=w.professional_shell.cockpit
  c.update_session({}, {'connected':False},None)
  self.assertEqual(c.grid.count(),0)
  self.assertFalse(c.empty.isHidden())
