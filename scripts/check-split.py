import sys
sys.path.insert(0,'build-input/app')
from PySide6.QtWidgets import QApplication,QSplitter
import native,split_workspace,transport
app=QApplication([]);w=native.Window();w.split_page();w.show();app.processEvents()
assert len(w.findChildren(QSplitter))==1
assert not w.findChildren(split_workspace.Trend)[0].samples
assert w.grab().save('dist/split-smoke.png')
w.findChildren(split_workspace.Trend)[0].sample(900);w.findChildren(split_workspace.Trend)[0].sample(1200)
assert len(w.findChildren(split_workspace.Trend)[0].samples)==2

# Standalone links reserve endpoints; no vehicle, frames, or commands sent here.
a=transport.Link();b=transport.Link()
try:
 try:a._connect('invalid','same')
 except ValueError:pass
 try:b._connect('invalid','same')
 except ConnectionError as e:assert 'already in use' in str(e)
 else:raise AssertionError('Shared adapter reservation not enforced')
finally:a.close();b.close()
print('Splitter, empty measurements and independent adapter reservation passed')
