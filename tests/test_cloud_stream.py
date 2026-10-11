import os,sys,tempfile,time,io,json
from pathlib import Path
os.environ.update(QT_QPA_PLATFORM='offscreen',GITM_STATE=tempfile.mkdtemp(),GITM_LANGUAGE='en')
sys.path.insert(0,str(Path('gitm-current/build-input/app').resolve()))
from PySide6.QtWidgets import QLabel,QApplication,QPushButton,QComboBox,QTextEdit,QTextBrowser,QCheckBox
from native import Window
import cloud_ui,cloud_backend
app=QApplication([]);w=Window();w.show();w.cloud_token='TEST_TOKEN_NOT_REAL'
def request(*a,**kw):return {'models':[{'id':'test/free','name':'Free fixture','free':True},{'id':'paid','free':False}]}
cloud_backend.request=request
requests=[]
class Response(io.BytesIO):
 def __enter__(self):return self
 def __exit__(self,*_):self.close()
def urlopen(req,timeout):
 requests.append(json.loads(req.data))
 return Response(b'data: {"choices":[{"delta":{"content":"TEST streamed "}}]}\n\ndata: {"choices":[{"delta":{"content":"answer"}}]}\n\ndata: [DONE]\n')
cloud_ui.urllib.request.urlopen=urlopen
w.ai_page()
def ev():app.processEvents()
def wait():
 end=time.monotonic()+5
 while getattr(w,'cloud_task',None) and w.cloud_task.isRunning() and time.monotonic()<end:ev();time.sleep(.01)
 from PySide6.QtTest import QTest
 QTest.qWait(50);ev();assert not w.cloud_task.isRunning()
wait();page=w.pages.currentWidget();models=page.findChildren(QComboBox)[1];assert models.count()==1
page.findChild(QCheckBox).setChecked(True);page.findChildren(QTextEdit)[-1].setPlainText('TEST P0300')
next(b for b in page.findChildren(QPushButton) if b.text()=='Send').click();wait()
assert 'TEST streamed answer' in page.findChild(QTextBrowser).toPlainText()
assert cloud_ui.sessions()[0][2][-1]['text']=='TEST streamed answer'
page.findChildren(QTextEdit)[-1].setPlainText('TEST next measurement')
next(b for b in page.findChildren(QPushButton) if b.text()=='Send').click();wait()
assert 'TEST streamed answer' in requests[-1]['prompt'];assert 'vin' not in requests[-1]
print('PASS mocked SSE stream, local persistence, conversation context, paid model excluded, no implicit VIN')
w.close();ev()
