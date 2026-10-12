import unittest
from pathlib import Path
import resource_workspace as resources
class CatalogTests(unittest.TestCase):
 def test_supplement_exposes_adapter_and_mechanics_sources_without_claiming_integration(self):
  rows=resources.catalog_extension()
  self.assertTrue(any('mechanics' in row['categories'] for row in rows))
  self.assertTrue(any('adapters' in row['categories'] for row in rows))
  self.assertTrue(all(row['integration_verified'] is False for row in rows))
 def test_search_matches_brand_and_protocol(self):
  row={'name':'Definition','makes':['Renault','Dacia'],'protocols':['KWP2000'],'categories':['electrical']}
  self.assertIn('renault',resources.searchable(row))
  self.assertIn('kwp2000',resources.searchable(row))
