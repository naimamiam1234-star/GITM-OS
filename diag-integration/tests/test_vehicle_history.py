import tempfile,unittest
from pathlib import Path
import store,vehicle_history
class Visits(unittest.TestCase):
 def setUp(self):
  self.old=store.BASE;self.tmp=tempfile.TemporaryDirectory();store.BASE=Path(self.tmp.name)
 def tearDown(self):store.BASE=self.old;self.tmp.cleanup()
 def test_reconnect_resumes_without_incrementing(self):
  car=dict(make='Renault',model='Clio',year=2020,engine='diesel')
  first,car=vehicle_history.begin_visit(car)
  again,car=vehicle_history.begin_visit(car)
  self.assertEqual(first,again);self.assertEqual(vehicle_history.profiles()[0]['visits'],1)
  second,car=vehicle_history.begin_visit(car,resume=False)
  self.assertNotEqual(first,second);self.assertEqual(vehicle_history.profiles()[0]['visits'],2)
 def test_identical_models_without_vin_are_distinct_vehicles(self):
  a=vehicle_history.remember(dict(make='Renault',model='Clio',year=2020))[0]
  b=vehicle_history.remember(dict(make='Renault',model='Clio',year=2020))[0]
  self.assertNotEqual(a,b)
 def test_invalid_vin_does_not_create_profile(self):
  with self.assertRaises(ValueError):vehicle_history.remember(dict(make='Renault',model='Clio',year=2020,vin='wrong'))
  self.assertEqual(vehicle_history.profiles(),[])
