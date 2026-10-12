import unittest,tempfile
from pathlib import Path
import system_services
class Services(unittest.TestCase):
 def test_general_calculator_is_os_kcalc(self):self.assertEqual(system_services.command('calculator'),['kcalc'])
 def test_pdf_uses_native_os_reader_and_exact_local_path(self):
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/'report.pdf';path.write_bytes(b'PDF');self.assertEqual(system_services.command('pdf',path),['okular',str(path.resolve())])
 def test_unknown_services_or_missing_files_rejected(self):
  with self.assertRaises(ValueError):system_services.command('unknown')
  with self.assertRaises(ValueError):system_services.command('pdf','/nonexistent/report.pdf')
