import json,tempfile,unittest
from pathlib import Path
import vehicle_definitions as d
class DefinitionTests(unittest.TestCase):
 def fixture(self):return {'make':'Test','model':'Example','generation':'A','market':'Test market','source':'Synthetic unit-test fixture','years':[2024,2026],'engines':[{'name':'Engine A','fuel':'Diesel','source':'Synthetic fixture','years':[2026]}]}
 def load(self,row):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'data.json';path.write_text(json.dumps([row]));return d.load(path)
 def test_model_and_engine_years_are_explicit(self):
  row=self.load(self.fixture())[0];self.assertEqual(row['years'],[2024,2026]);self.assertEqual(d.engines(row,2024),[]);self.assertEqual(len(d.engines(row,2026)),1)
 def test_unrelated_engine_year_rejected(self):
  row=self.fixture();row['engines'][0]['years']=[2020]
  with self.assertRaises(ValueError):self.load(row)
 def test_missing_source_rejected(self):
  row=self.fixture();row.pop('source')
  with self.assertRaises(ValueError):self.load(row)
 def test_brand_filter_does_not_mix_makes(self):self.assertEqual(d.models([self.fixture()],'Other'),[])
