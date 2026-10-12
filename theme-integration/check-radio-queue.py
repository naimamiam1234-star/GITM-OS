"""A failed process start must release queued connectivity requests."""
import sys, tempfile, time
from pathlib import Path
from unittest.mock import patch
from PySide6.QtWidgets import QApplication, QWidget
sys.path.insert(0, str(Path('patches').resolve()))
from desktop_radios import Radios
app=QApplication([]); host=QWidget()
with patch.object(Radios,'refresh',lambda self:None): radio=Radios(host)
radio.timer.stop(); results=[]
with tempfile.TemporaryDirectory() as directory:
 broken=Path(directory)/'broken'; broken.write_text('#!/missing-gitm-interpreter\n'); broken.chmod(0o755)
 radio.run([str(broken)],lambda ok,out:results.append(('failed',ok)))
 radio.run(['/bin/echo','second request'],lambda ok,out:results.append(('next',ok)))
 deadline=time.monotonic()+2
 while time.monotonic()<deadline and len(results)<2:
  app.processEvents();time.sleep(.01)
 assert results==[('failed',False),('next',True)],results
 assert not radio.busy and not radio.pending
print('Failed start releases queue; following real process completes')
