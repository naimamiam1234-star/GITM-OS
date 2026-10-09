"""Two real diagnostic views; no generated sensor samples."""
import json,time
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter,QColor,QPen
from PySide6.QtWidgets import QSplitter,QWidget,QVBoxLayout,QLabel,QTextEdit,QPushButton
import diagnostics,store

class Trend(QWidget):
 def __init__(self):
  super().__init__();self.samples=[];self.setMinimumHeight(140)
 def sample(self,value):
  if isinstance(value,(int,float)):
   self.samples.append((time.monotonic(),float(value)));self.samples=self.samples[-120:];self.update()
 def paintEvent(self,event):
  p=QPainter(self);p.fillRect(self.rect(),QColor('#102238'));p.setPen(QColor('#bbd6ee'));p.drawText(12,22,'RPM · measured samples')
  if len(self.samples)<2:p.drawText(12,60,'Waiting for vehicle measurements');return
  values=[v for t,v in self.samples];lo=min(values);hi=max(values);span=max(1,hi-lo);t0=self.samples[0][0];duration=max(.001,self.samples[-1][0]-t0)
  from PySide6.QtCore import QPointF
  p.setPen(QPen(QColor('#39baff'),2));previous=None
  for t,v in self.samples:
   point=QPointF(12+(t-t0)/duration*(self.width()-24),self.height()-15-(v-lo)/span*(self.height()-55))
   if previous is not None:p.drawLine(previous,point)
   previous=point


def show(window):
 l=window.page('Split Screen · الأعطال والبيانات الحية')
 l.addWidget(QLabel('تُقرأ البيانات من المحول المتصل. لا تُعرض قياسات قبل وصول استجابة صحيحة.'))
 splitter=QSplitter(Qt.Horizontal);l.addWidget(splitter,1)
 left=QWidget();lv=QVBoxLayout(left);lv.addWidget(QLabel('DTC'));faults=QTextEdit();faults.setReadOnly(True);lv.addWidget(faults);splitter.addWidget(left)
 right=QWidget();rv=QVBoxLayout(right);rv.addWidget(QLabel('Live Data'));values=QTextEdit();values.setReadOnly(True);rv.addWidget(values);trend=Trend();rv.addWidget(trend);splitter.addWidget(right);splitter.setSizes([400,600])
 # Use the application's one background task slot: avoid overlapping adapter requests.
 def run(command,out):
  if window.task is not None and window.task.isRunning():return
  def measured():
   result=diagnostics.read(command);store.save(window.vehicle,command,result);return result
  window.run(measured,out)
  if command=='LIVE':window.task.result.connect(lambda result:trend.sample(result.get('RPM',{}).get('value')))
 for title,command,out in [('قراءة الأعطال','DTC',faults),('تحديث البيانات الحية','LIVE',values)]:
  b=QPushButton(title);b.clicked.connect(lambda checked=False,c=command,o=out:run(c,o));l.addWidget(b)
 window.button(l,'جلسة سيارة ثانية · تتطلب محولًا مستقلًا',lambda:second(window))

def second(window):
 from PySide6.QtWidgets import QMessageBox
 import subprocess,sys
 from pathlib import Path
 if QMessageBox.question(window,'Dual Diagnosis','فتح جلسة مستقلة؟ صِل محولًا ثانيًا واختره يدويًا في النافذة الجديدة.')==QMessageBox.Yes:
  subprocess.Popen([sys.executable,str(Path(__file__).parent/'native.py'),'--skip-intro','--secondary'])
