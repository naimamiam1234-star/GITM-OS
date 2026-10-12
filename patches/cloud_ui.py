"""Cloudflare-only session authentication, AI, web and video research."""
import html,json,threading,urllib.request
from urllib.parse import urlencode
from PySide6.QtCore import Qt,QThread,Signal
from PySide6.QtWidgets import QLabel,QLineEdit,QPushButton,QHBoxLayout,QTextEdit,QTextBrowser,QComboBox,QCheckBox
import cloud_backend
from workshop_tools import t
class Worker(QThread):
 done=Signal(object);error=Signal(str);chunk=Signal(str)
 def __init__(self,fn):super().__init__();self.fn=fn
 def run(self):
  try:self.done.emit(self.fn())
  except Exception as e:self.error.emit(str(e))
def show(w):
 l=w.page(t('مساعد GITM','Assistant GITM','GITM Assistant'))
 l.addWidget(QLabel(t('اتصال آمن بخادم GITM · لا تحتاج مفتاح مزوّد داخل النظام','Connexion sécurisée au serveur GITM','Secure GITM backend · no provider key on this device')))
 row=QHBoxLayout();email=QLineEdit();email.setPlaceholderText('Email');password=QLineEdit();password.setPlaceholderText(t('كلمة المرور','Mot de passe','Password'));password.setEchoMode(QLineEdit.Password);login=QPushButton(t('تسجيل الدخول','Connexion','Sign in'))
 for item in (email,password,login):row.addWidget(item)
 l.addLayout(row);models=QComboBox();models.setPlaceholderText(t('نماذج مجانية فقط','Modèles gratuits uniquement','Free models only'));l.addWidget(models)
 mode=QComboBox();mode.addItems([t('المساعد','Assistant','Assistant'),t('بحث الويب','Recherche web','Web search'),'YouTube']);l.addWidget(mode)
 history=QTextBrowser();history.setOpenExternalLinks(True);l.addWidget(history,1)
 prompt=QTextEdit();prompt.setMaximumHeight(130);prompt.setPlaceholderText(t('اكتب السؤال أو العَرَض وكود العطل…','Question, symptôme ou code défaut…','Question, symptom or fault code…'));l.addWidget(prompt)
 consent=QCheckBox(t('أوافق على إرسال النص المكتوب؛ لا يُرسل VIN تلقائيًا','Envoyer uniquement le texte saisi','Send entered text only; VIN is not sent automatically'));l.addWidget(consent)
 send=QPushButton(t('إرسال','Envoyer','Send'));l.addWidget(send)
 def busy():return getattr(w,'cloud_task',None) is not None and w.cloud_task.isRunning()
 def run(fn,done):
  if busy():return
  task=Worker(fn);w.cloud_task=task;task.done.connect(done);task.error.connect(lambda e:history.append(html.escape(e)));task.chunk.connect(lambda text:history.insertPlainText(text));task.start()
 def load_models():
  run(lambda:cloud_backend.request('/v1/models',token=w.cloud_token),lambda d:[models.addItem(m.get('name',m['id']),m['id']) for m in d.get('models',[])])
 def authenticated(d):
  w.cloud_token=d['idToken'];password.clear();history.append(t('تم تسجيل الدخول؛ ينتهي الاتصال عند انتهاء صلاحية الجلسة.','Connecté; la session expire automatiquement.','Signed in; session expiry requires signing in again.'))
  # Start only after the login thread has completed.
  w.cloud_task.finished.connect(load_models)
 def signin():
  if not email.text() or not password.text():return
  payload={'email':email.text(),'password':password.text()}
  run(lambda:cloud_backend.request('/v1/auth/login',payload),authenticated)
 login.clicked.connect(signin)
 def submit():
  token=getattr(w,'cloud_token',None);text=prompt.toPlainText().strip()
  if not token or not text or not consent.isChecked():history.append(t('سجّل الدخول واكتب السؤال ووافق على إرساله.','Connexion et consentement requis.','Sign in, enter a question and consent first.'));return
  if busy():return
  history.append('<p><b>'+html.escape(text)+'</b></p>');prompt.clear()
  if mode.currentIndex()==0:
   model=models.currentData()
   if not model:history.append('No free model loaded');return
   def chat():
    req=urllib.request.Request(cloud_backend.BASE+'/v1/ai/chat',data=json.dumps({'prompt':text,'model':model}).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+token})
    with urllib.request.urlopen(req,timeout=30) as response:
     total=0
     while line:=response.readline(65537):
      total+=len(line)
      if total>2*1024*1024 or len(line)>65536:raise ValueError('Response exceeds limit')
      if not line.startswith(b'data:'):continue
      data=line[5:].strip()
      if data==b'[DONE]':break
      item=json.loads(data)
      if item.get('error'):raise ValueError('AI provider unavailable')
      for choice in item.get('choices',[]):
       part=choice.get('delta',{}).get('content')
       if part:w.cloud_task.chunk.emit(part)
    return None
   run(chat,lambda _:history.append(''))
  else:
   video=mode.currentIndex()==2
   def results(d):
    for item in d.get('videos' if video else 'results',[]):
     url=item.get('url','')
     if url.startswith(('https://','http://')):history.append('<p><a href="'+html.escape(url,quote=True)+'">'+html.escape(item.get('title',url))+'</a><br>'+html.escape(item.get('content',item.get('channel','')))+'</p>')
   run(lambda:cloud_backend.request('/v1/videos?'+urlencode({'q':text}),token=token) if video else cloud_backend.request('/v1/search',{'query':text},token),results)
 send.clicked.connect(submit)
 if getattr(w,'cloud_token',None):load_models()
