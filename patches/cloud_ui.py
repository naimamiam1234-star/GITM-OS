"""Cloudflare AI research workspace; credentials are session-only, history is local."""
import html,json,urllib.request,threading,uuid
from urllib.parse import urlencode
from PySide6.QtCore import Qt,QThread,Signal
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (QLabel,QLineEdit,QPushButton,QHBoxLayout,QVBoxLayout,
 QTextEdit,QTextBrowser,QComboBox,QCheckBox,QListWidget,QWidget)
import cloud_backend,store
from workshop_tools import t
class Worker(QThread):
 done=Signal(object);error=Signal(str);chunk=Signal(str)
 def __init__(self,fn):super().__init__();self.fn=fn;self.cancel=threading.Event()
 def run(self):
  try:self.done.emit(self.fn(self))
  except Exception as e:self.error.emit(str(e))

def sessions():
 with store.db() as c:
  c.execute('CREATE TABLE IF NOT EXISTS conversations(id TEXT PRIMARY KEY,title TEXT,body TEXT)')
  return [(i,title,json.loads(body)) for i,title,body in c.execute('SELECT id,title,body FROM conversations ORDER BY rowid DESC LIMIT 100')]
def save_session(id,title,messages):
 with store.db() as c:
  c.execute('CREATE TABLE IF NOT EXISTS conversations(id TEXT PRIMARY KEY,title TEXT,body TEXT)')
  c.execute('INSERT OR REPLACE INTO conversations VALUES(?,?,?)',(id,title,json.dumps(messages,ensure_ascii=False)))

def show(w):
 # Keep the active workspace alive while its background thread streams.
 if getattr(w,'cloud_task',None) and w.cloud_task.isRunning():return
 l=w.page(t('مساعد GITM','Assistant GITM','GITM Assistant'))
 cloud_page=w.pages.currentWidget()
 account=QHBoxLayout();l.addLayout(account)
 account.addWidget(QLabel(t('مفاتيح الخدمات محفوظة على خادم GITM','Clés conservées sur le serveur GITM','Provider keys stay on the GITM server')),1)
 toggle=QPushButton(t('اتصال الحساب','Connexion du compte','Account connection'));account.addWidget(toggle)
 auth=QWidget();ar=QHBoxLayout(auth);ar.setContentsMargins(0,0,0,0)
 email=QLineEdit();email.setPlaceholderText('Email');password=QLineEdit();password.setPlaceholderText(t('كلمة المرور','Mot de passe','Password'));password.setEchoMode(QLineEdit.Password)
 login=QPushButton(t('تسجيل الدخول','Connexion','Sign in'))
 for item in (email,password,login):ar.addWidget(item)
 l.addWidget(auth);auth.hide();toggle.clicked.connect(lambda:auth.setVisible(not auth.isVisible()))
 workspace=QHBoxLayout();l.addLayout(workspace,1)
 sidebar=QVBoxLayout();workspace.addLayout(sidebar,1)
 new=QPushButton(t('محادثة جديدة','Nouvelle conversation','New conversation'));sidebar.addWidget(new)
 recent=QListWidget();recent.setMinimumWidth(170);recent.setMaximumWidth(240);sidebar.addWidget(recent,1)
 main=QVBoxLayout();workspace.addLayout(main,4)
 options=QHBoxLayout();main.addLayout(options)
 mode=QComboBox();mode.addItems([t('المساعد','Assistant','Assistant'),t('بحث الويب','Recherche web','Web search'),'YouTube']);options.addWidget(mode)
 models=QComboBox();models.setPlaceholderText(t('نماذج مجانية فقط','Modèles gratuits','Free models only'));options.addWidget(models,1)
 history=QTextBrowser();history.setOpenExternalLinks(True);main.addWidget(history,1)
 prompt=QTextEdit();prompt.setMaximumHeight(110);prompt.setPlaceholderText(t('اسأل عن العطل أو خطوات الفحص…','Question sur un défaut ou un contrôle…','Ask about a fault or the next test…'));main.addWidget(prompt)
 seed=getattr(w,'assistant_seed','');prompt.setPlainText(seed);w.assistant_seed=''
 consent=QCheckBox(t('إرسال السؤال وسياق المحادثة؛ لا يُرسل VIN تلقائيًا','Envoyer la conversation; VIN exclu','Send conversation context; VIN is not sent automatically'));main.addWidget(consent)
 row=QHBoxLayout();main.addLayout(row);feedback=QLabel();row.addWidget(feedback,1)
 send=QPushButton(t('إرسال','Envoyer','Send'));stop=QPushButton(t('إيقاف','Arrêter','Stop'));stop.setEnabled(False);row.addWidget(stop);row.addWidget(send)
 state={'id':str(uuid.uuid4()),'messages':[],'stream':'','title':''}
 def refresh():
  recent.clear()
  for id,title,messages in sessions():recent.addItem(title);recent.item(recent.count()-1).setData(Qt.UserRole,(id,title,messages))
 def persist():
  if state['messages']:save_session(state['id'],state['title'],state['messages'])
 def display():
  history.clear()
  if not state['messages']:
   history.setHtml('<h2>'+t('ما الذي نفحصه اليوم؟','Que diagnostiquons-nous ?','What are we investigating today?')+'</h2><p>'+t('اكتب الأعراض والكود والقياسات. اطلب الأدلة وخطوة الفحص التالية.','Décrivez symptômes, codes et mesures.','Describe symptoms, codes and measurements. Ask for evidence and the next test.')+'</p>')
  for item in state['messages']:history.append('<p><b>'+html.escape(item['role'])+'</b></p><p>'+html.escape(item['text']).replace('\n','<br>')+'</p>')
 def fresh():
  if getattr(w,'cloud_task',None) and w.cloud_task.isRunning():return
  state.update(id=str(uuid.uuid4()),messages=[],stream='',title='');display()
 new.clicked.connect(fresh)
 def select(item):
  if getattr(w,'cloud_task',None) and w.cloud_task.isRunning():return
  id,title,messages=item.data(Qt.UserRole);state.update(id=id,title=title,messages=messages,stream='');display()
 recent.itemClicked.connect(select);refresh();display()
 def run(fn,done):
  if getattr(w,'cloud_task',None) and w.cloud_task.isRunning():return
  w.tool_pages['cloud-workspace']=cloud_page
  task=Worker(fn);w.cloud_task=task;send.setEnabled(False);new.setEnabled(False);recent.setEnabled(False);stop.setEnabled(True)
  task.done.connect(done)
  task.error.connect(lambda e:feedback.setText(str(e)))
  def chunk(text):
   state['stream']+=text;cursor=history.textCursor();cursor.movePosition(QTextCursor.End);cursor.insertText(text);history.setTextCursor(cursor)
  task.chunk.connect(chunk)
  def finish():
   if w.tool_pages.get('cloud-workspace') is cloud_page:w.tool_pages.pop('cloud-workspace',None)
   if state['stream']:
    state['messages'].append({'role':'assistant','text':state['stream']});state['stream']='';persist();refresh()
   send.setEnabled(True);new.setEnabled(True);recent.setEnabled(True);stop.setEnabled(False)
  task.finished.connect(finish);task.start()
 def load_models():
  def loaded(d):
   models.clear()
   for m in d.get('models',[]):
    id=m.get('id','')
    if m.get('free') is True:models.addItem(m.get('name',id),id)
   if models.count():models.setCurrentIndex(0)
  run(lambda _:cloud_backend.request('/v1/models',token=w.cloud_token),loaded)
 def signin():
  if not email.text().strip() or not password.text():return
  payload={'email':email.text().strip(),'password':password.text()}
  def authenticated(d):
   w.cloud_token=d['idToken'];password.clear();auth.hide();feedback.setText(t('تم الاتصال','Connecté','Connected'));w.cloud_task.finished.connect(load_models)
  run(lambda _:cloud_backend.request('/v1/auth/login',payload),authenticated)
 login.clicked.connect(signin)
 stop.clicked.connect(lambda:w.cloud_task.cancel.set() if getattr(w,'cloud_task',None) else None)
 def submit():
  text=prompt.toPlainText().strip();token=getattr(w,'cloud_token',None)
  if not token or not text or not consent.isChecked():feedback.setText(t('سجّل الدخول واكتب السؤال ووافق على إرساله.','Connexion, question et consentement requis.','Sign in, enter a question and consent first.'));return
  if mode.currentIndex()==0 and not models.currentData():feedback.setText(t('لم يتوفر نموذج مجاني','Aucun modèle gratuit','No free model available'));return
  state['title']=state['title'] or text[:60];state['messages'].append({'role':'user','text':text});persist();display();prompt.clear();feedback.clear()
  if mode.currentIndex()==0:
   model=models.currentData();context='\n\n'.join(m['role']+': '+m['text'] for m in state['messages'][-12:])[-12000:]
   history.append('<p><b>GITM AI</b></p>')
   def chat(task):
    req=urllib.request.Request(cloud_backend.BASE+'/v1/ai/chat',data=json.dumps({'prompt':context,'model':model}).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+token})
    with urllib.request.urlopen(req,timeout=30) as response:
     total=0
     while not task.cancel.is_set():
      line=response.readline(65537)
      if not line:break
      total+=len(line)
      if total>2*1024*1024 or len(line)>65536:raise ValueError('Response exceeds limit')
      if not line.startswith(b'data:'):continue
      data=line[5:].strip()
      if data==b'[DONE]':break
      item=json.loads(data)
      if item.get('error'):raise ValueError('AI provider unavailable')
      for choice in item.get('choices',[]):
       part=choice.get('delta',{}).get('content')
       if part:task.chunk.emit(part)
   run(chat,lambda _:None)
  else:
   video=mode.currentIndex()==2
   def results(d):
    items=d.get('videos' if video else 'results',[]);body=[]
    for item in items:
     url=item.get('url','')
     if url.startswith(('https://','http://')):
      body.append(item.get('title',url)+'\n'+url+'\n'+item.get('content',item.get('channel','')))
      history.append('<p><a href="'+html.escape(url,quote=True)+'">'+html.escape(item.get('title',url))+'</a><br>'+html.escape(item.get('content',item.get('channel','')))+'</p>')
    if not body:body=[t('لا توجد نتائج','Aucun résultat','No results')]
    state['messages'].append({'role':'YouTube' if video else 'Web','text':'\n\n'.join(body)});persist();refresh()
   run(lambda _:cloud_backend.request('/v1/videos?'+urlencode({'q':text}),token=token) if video else cloud_backend.request('/v1/search',{'query':text},token),results)
 send.clicked.connect(submit)
 if getattr(w,'cloud_token',None):load_models()
