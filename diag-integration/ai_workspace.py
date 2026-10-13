"""Explicit cloud consent and de-identified current-scan attachment."""
import json,re,threading
from pathlib import Path
from html import escape
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QLineEdit,QComboBox,QTextEdit,QTextBrowser,QCheckBox,QLabel,QMessageBox
from professional_components import triple,action_button

def sanitized_scan(report):
 # Whitelist structured observations. Raw trace/error strings can contain identity.
 allowed={'format','status','scope','evidence','protocol','ecus','dtc','stored','pending','permanent','codes','readiness','MIL','stored_dtc_count','engine_type','monitors','name','supported','complete','freeze','frame','trigger_dtc','values','pid','value','unit','id','live','ecu','at','started_at','finished_at','vehicle','make','model','year','engine','errors','error','section'}
 vins=[]
 def identities(v,sensitive=False):
  if isinstance(v,dict):
   for k,x in v.items():
    personal=sensitive or k.casefold() in ('vin','client','customer','phone','email','plate','registration')
    if personal and isinstance(x,str):vins.append(x)
    identities(x,personal)
  elif isinstance(v,list):
   for x in v:identities(x,sensitive)
 identities(report)
 def clean(v):
  if isinstance(v,dict):return {k:clean(x) for k,x in v.items() if k in allowed}
  if isinstance(v,list):return [clean(x) for x in v]
  if isinstance(v,str):
   for vin in vins:
    if vin:v=v.replace(vin,'[redacted]')
   return re.sub(r'\b[A-HJ-NPR-Z0-9]{17}\b','[redacted VIN]',v,flags=re.I)
  return v
 return clean(report)

def current_scan(window):
 for name in ('_diagnostic_workspace','_obd_workspace','diagnostic_workspace','workspace'):
  widget=getattr(window,name,None)
  if isinstance(getattr(widget,'report',None),dict) and widget.report.get('vehicle')==window.vehicle:return widget.report
 from diagnostic_workspace import Workspace
 for child in window.findChildren(Workspace):
  if isinstance(getattr(child,'report',None),dict) and child.report.get('vehicle')==window.vehicle:return child.report
 return None

class Assistant(QWidget):
 def __init__(self,window):
  super().__init__();self.window=window;self.attachment=None;self.cancel_event=None;layout=QVBoxLayout(self)
  info=QLabel(triple('مساعد سحابي يشرح ولا ينفذ أوامر السيارة. المفتاح في ذاكرة الجلسة فقط.','Assistant cloud explicatif, sans commande véhicule. Clé en mémoire de session.','Cloud assistant explains and cannot execute vehicle commands. Key stays in session memory.'));info.setWordWrap(True);layout.addWidget(info)
  row=QHBoxLayout();self.key=QLineEdit(getattr(window,'openrouter_key',''));self.key.setObjectName('openrouterKey');self.key.setEchoMode(QLineEdit.Password);self.key.setPlaceholderText('OpenRouter API key');self.key.setLayoutDirection(Qt.LeftToRight);self.key.textChanged.connect(lambda v:setattr(window,'openrouter_key',v));row.addWidget(self.key,1);self.model=QComboBox();self.model.addItem('openrouter/free')
  try:
   import native
   snapshot=json.loads((Path(native.__file__).parent/'free-models-snapshot.json').read_text());self.model.addItems([m['id'] for m in snapshot['models'] if m['id']!='openrouter/free'])
  except (OSError,ValueError,KeyError):pass
  self.model.setMinimumContentsLength(12);self.model.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon);self.model.setMaximumWidth(230);self.key.setMinimumWidth(120)
  row.addWidget(self.model,1);layout.addLayout(row)
  self.conversation=QTextBrowser();layout.addWidget(self.conversation,1);self.prompt=QTextEdit();self.prompt.setMaximumHeight(115);self.prompt.setPlaceholderText(triple('اكتب سؤالك دون بيانات شخصية','Question sans données personnelles','Ask without personal information'));layout.addWidget(self.prompt)
  self.consent=self.wrapped_consent(triple('أوافق على إرسال السؤال والمعاينة المعتمدة إلى OpenRouter','J’autorise l’envoi de la question et de l’aperçu approuvé à OpenRouter','I approve sending the question and approved preview to OpenRouter'),layout)
  self.preview=QTextBrowser();self.preview.setMaximumHeight(110);self.preview.hide();layout.addWidget(self.preview)
  self.approve=QCheckBox(triple('أوافق على إرفاق هذه المعاينة','J’approuve cet aperçu joint','Approve this attachment preview'));self.approve.hide();layout.addWidget(self.approve)
  actions=QGridLayout();attach=action_button(triple('معاينة الفحص الحالي','Aperçu du scan actuel','Preview current scan'));attach.clicked.connect(self.attach);actions.addWidget(attach,0,0);detach=action_button(triple('إزالة المرفق','Retirer la pièce jointe','Remove attachment'));detach.clicked.connect(self.detach);actions.addWidget(detach,0,1);self.send_button=action_button(triple('إرسال','Envoyer','Send'),role='primary');self.send_button.clicked.connect(self.send);actions.addWidget(self.send_button,1,0);self.cancel_button=action_button(triple('إلغاء','Annuler','Cancel'));self.cancel_button.clicked.connect(self.cancel);self.cancel_button.setEnabled(False);actions.addWidget(self.cancel_button,1,1);layout.addLayout(actions);self.feedback=QLabel();self.feedback.setWordWrap(True);layout.addWidget(self.feedback)
 def wrapped_consent(self,text,layout):
  row=QHBoxLayout();check=QCheckBox();check.setAccessibleName(text);row.addWidget(check);label=QLabel(text);label.setWordWrap(True);row.addWidget(label,1);layout.addLayout(row);return check
 def attach(self):
  if hasattr(self,'session_capture'):self.session_capture();return
  self.evidence_override=None
  scan=current_scan(self.window);self.approve.setChecked(False)
  self.attachment=sanitized_scan(scan) if scan else None
  self.preview.setPlainText(json.dumps(self.attachment,ensure_ascii=False,indent=2) if scan else triple('لا يوجد فحص حالي','Aucun scan actuel','No current scan'));self.preview.show();self.approve.setVisible(bool(scan))
 def detach(self):
  self.attachment=None;self.evidence_override=None;self.preview.hide();self.approve.setChecked(False);self.approve.hide()
 def cancel(self):
  if self.cancel_event:self.cancel_event.set();self.feedback.setText(triple('جارٍ الإلغاء','Annulation en cours','Cancelling'))
 def hideEvent(self,event):self.cancel();super().hideEvent(event)
 def send(self):
  window=self.window
  if not self.consent.isChecked():self.feedback.setText(triple('الموافقة مطلوبة','Consentement requis','Consent is required'));return
  if getattr(window,'cloud_task',None) is not None and window.cloud_task.isRunning():return
  key=self.key.text();prompt=self.prompt.toPlainText();model=self.model.currentText()
  if not key or not prompt.strip():self.feedback.setText(triple('المفتاح والسؤال مطلوبان','Clé et question requises','Key and question are required'));return
  if self.attachment is not None and not self.approve.isChecked():self.feedback.setText(triple('اعتمد المعاينة أولاً','Approuver l’aperçu','Approve the attachment preview first'));return
  evidence=getattr(self,'evidence_override',None) or ([{'id':'E1','type':'deidentified_observed_scan','data':self.attachment}] if self.attachment else [])
  from native import ChatTask
  from shiboken6 import isValid
  self.request_failed=False;self.cancel_event=threading.Event();window.ai_cancel=self.cancel_event;task=ChatTask(key,model,prompt,self.cancel_event,evidence);task.setParent(window);window.cloud_task=task
  self.response_text='';completion=getattr(self,'on_complete',None)
  self.conversation.append('<p><b>'+triple('أنت','Vous','You')+'</b><br>'+escape(prompt)+'</p><p><b>GITM</b></p>');self.send_button.setEnabled(False);self.cancel_button.setEnabled(True);self.feedback.setText(triple('طلب جارٍ','Requête en cours','Request in progress'))
  def chunk(text):
   if isValid(self):self.response_text+=text;self.conversation.insertPlainText(text)
  task.chunk.connect(chunk)
  def failed(error):
   if isValid(self):self.request_failed=True;self.feedback.setText(str(error).replace(key,'[redacted]'))
  task.failure.connect(failed)
  def finished():
   if isValid(self):
    self.send_button.setEnabled(True);self.cancel_button.setEnabled(False)
    if not self.request_failed:self.feedback.setText(triple('انتهى الطلب','Requête terminée','Request finished'))
    if completion:completion({'question':prompt,'answer':self.response_text,'status':'failed' if self.request_failed else 'cancelled' if self.cancel_event.is_set() else 'complete','model':model})
   if getattr(window,'cloud_task',None) is task:window.cloud_task=None
   task.deleteLater()
  task.finished.connect(finished);task.start()

def show(window):
 layout=window.page(triple('المساعد الذكي','Assistant IA','AI assistant'));widget=Assistant(window);layout.addWidget(widget);return widget
