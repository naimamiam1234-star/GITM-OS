import unittest
from unittest.mock import patch
from adapter_registry import Registry,Definition,default_registry
class RegistryTests(unittest.TestCase):
 def test_catalog_is_passive_and_plans_not_executable(self):
  with patch('transport.LINK.connect') as connect:
   rows=default_registry().catalog();connect.assert_not_called()
  self.assertEqual(len(rows),8);self.assertTrue(all(not row['executable'] for row in rows if row['implementation']=='planned'))
 def test_elm_uses_existing_shared_channel(self):
  import transport
  self.assertIs(default_registry().create('elm'),transport.LINK)
 def test_unknown_or_planned_connector_rejected(self):
  for name in ('missing','doip','socketcan'):
   with self.assertRaises(ValueError):default_registry().create(name)
 def test_duplicate_connector_rejected(self):
  r=default_registry()
  with self.assertRaises(ValueError):r.register(r.definitions['elm'])
 def test_incomplete_connector_rejected(self):
  r=Registry();r.register(Definition('test','Synthetic test connector',(),(),'implemented','not_tested','Unit-test fixture',lambda:object()))
  with self.assertRaises(ValueError):r.create('test')
