import unittest
from pathlib import Path
import vehicle_resources as r
class ResourceTests(unittest.TestCase):
 def test_model_names_do_not_claim_years_or_engines(self):
  rows=r.read('models.json');self.assertEqual(len(rows),2523);self.assertEqual(len({x['make'].casefold() for x in rows}),69)
  self.assertTrue(all('years' not in row and 'engines' not in row for row in rows))
 def test_makes_filtered_without_cross_brand_data(self):
  self.assertTrue(r.models('BMW'));self.assertTrue(all(x['make'].casefold()=='bmw' for x in r.models('BMW')));self.assertEqual(r.models('Nonexistent fixture'),[])
 def test_all184_assets_available_offline(self):
  self.assertEqual(len(r.logos()),184)
  self.assertTrue(all(Path(row['resolved_path']).is_file() for row in r.logos().values()))
