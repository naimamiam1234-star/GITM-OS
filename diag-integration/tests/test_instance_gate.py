import tempfile,unittest,time
from pathlib import Path
from PySide6.QtWidgets import QApplication
class InstanceGateTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
 def test_second_launcher_forwards_only_known_intents(self):
  from instance_gate import InstanceGate
  with tempfile.TemporaryDirectory() as d:
   first=InstanceGate(Path(d));second=InstanceGate(Path(d));events=[]
   self.assertTrue(first.acquire([],events.append));self.addCleanup(first.close)
   self.assertFalse(second.acquire(['--assistant','--untrusted'],lambda value:None))
   until=time.monotonic()+2
   while not events and time.monotonic()<until:self.app.processEvents();time.sleep(.01)
   self.assertEqual(events,[['--assistant']])
   first.close();third=InstanceGate(Path(d));self.assertTrue(third.acquire([],events.append));third.close()
 def test_startup_does_not_discard_queued_shortcut(self):
  from instance_gate import InstanceGate
  with tempfile.TemporaryDirectory() as d:
   gate=InstanceGate(Path(d));events=[]
   with gate.db() as db:db.execute('INSERT INTO requests(assistant) VALUES(1)')
   self.assertTrue(gate.acquire([],events.append));self.addCleanup(gate.close)
   gate.poll();self.assertEqual(events,[['--assistant']]);gate.close()
 def test_known_tool_survives_second_launcher(self):
  from instance_gate import InstanceGate
  with tempfile.TemporaryDirectory() as d:
   gate=InstanceGate(Path(d));second=InstanceGate(Path(d));events=[]
   self.assertTrue(gate.acquire([],events.append));self.addCleanup(gate.close)
   self.assertFalse(second.acquire(['--tool','customers'],lambda value:None))
   gate.poll();self.assertEqual(events,[['--tool','customers']]);gate.close()
