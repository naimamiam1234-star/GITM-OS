import unittest, pathlib, sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import transport
from install import patch_transport,patch_legacy_main
from obd_simulator import Simulator

class Generation(unittest.TestCase):
 def test_legacy_application_dock_is_removed_idempotently(self):
  import native
  code=pathlib.Path(native.__file__).read_text();patched=patch_legacy_main(code)
  self.assertNotIn('    from desktop_shell import Dock\n',patched);self.assertIn('w.showMaximized()',patched);self.assertEqual(patch_legacy_main(patched),patched)
 def test_same_endpoint_reconnect_changes_generation(self):
  raw=pathlib.Path(transport.__file__).read_text();patched=patch_transport(raw)
  self.assertEqual(patch_transport(patched),patched)
  scope={};exec(compile(patched,'patched_transport','exec'),scope)
  link=scope['Link']();sim=Simulator().start()
  try:
   target=f'127.0.0.1:{sim.port}';link.connect('wifi',target,family='elm');first=link.generation
   link.close();link.connect('wifi',target,family='elm')
   self.assertGreater(link.generation,first)
  finally:link.close();sim.stop()

if __name__=='__main__':unittest.main()
