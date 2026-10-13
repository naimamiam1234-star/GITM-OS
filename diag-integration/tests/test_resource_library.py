import tempfile,unittest,json
from pathlib import Path
class ResourceFiles(unittest.TestCase):
 def test_catalog_distinguishes_present_missing_and_escaping_paths(self):
  import resource_library
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'source.zip').write_bytes(b'archive')
   rows=[{'name':'local','path':'source.zip'},{'name':'missing','path':'missing.zip'},{'name':'outside','path':'../private.zip'}]
   (root/'catalog.json').write_text(json.dumps(rows))
   result=resource_library.catalog(root)
   self.assertTrue(result[0]['present']);self.assertFalse(result[1]['present']);self.assertFalse(result[2]['present']);self.assertIsNone(result[2]['local_path'])
 def test_cached_library_reuses_page(self):
  from PySide6.QtWidgets import QApplication
  app=QApplication.instance() or QApplication([])
  import native,resource_library
  w=native.Window();self.addCleanup(w.close)
  first=resource_library.show(w);count=w.pages.count();w.go_home();second=resource_library.show(w)
  self.assertIs(first,second);self.assertEqual(w.pages.count(),count)
