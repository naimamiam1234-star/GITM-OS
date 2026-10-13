"""One session-side assistant. It only receives snapshots; it never calls VCI."""
import json, threading
from html import escape
from PySide6.QtCore import Qt,QThread,Signal,QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QTextBrowser,QTextEdit,QCheckBox,QLineEdit,QTabWidget,QScrollArea,QDialog
import assistant_core as core
from ai_workspace import Assistant
from professional_components import triple as t,action_button

class SearchTask(QThread):
 result=Signal(object);failure=Signal(str)
 def __init__(self,query,provider,key,consent,cancel,parent):
  super().__init__(parent);self.args=(query,provider,key,consent,cancel)
 def run(self):
  try:self.result.emit(core.search_external(*self.args))
  except Exception as error:self.failure.emit(str(error).replace(self.args[2],'[redacted]') if self.args[2] else str(error))

class SessionAssistant(QWidget):
 def __init__(self,window):
  super().__init__();self.window=window;self.context=None;self.sources=[];self.search_task=None;self.search_cancel=None;self.expanded=False
  layout=QVBoxLayout(self);layout.setContentsMargins(10,10,10,10)
  title=QHBoxLayout();label=QLabel(t('المساعد التشخيصي','Assistant de session','Session assistant'));label.setObjectName('pageTitle');title.addWidget(label,1)
  self.expand=action_button(t('توسيع','Agrandir','Expand'));self.expand.clicked.connect(self.toggle_expanded);title.addWidget(self.expand)
  close=action_button('×');close.setAccessibleName(t('إخفاء المساعد','Masquer','Hide assistant'));close.clicked.connect(self.hide);title.addWidget(close);layout.addLayout(title)
  self.identity=QLabel();self.identity.setWordWrap(True);layout.addWidget(self.identity)
  self.symptoms=QTextEdit();self.symptoms.setMaximumHeight(68);self.symptoms.setPlaceholderText(t('الأعراض وملاحظات الفني؛ دون بيانات شخصية','Symptômes sans données personnelles','Symptoms and technician notes; no personal details'));layout.addWidget(self.symptoms)
  self.refresh_button=action_button(t('اعتماد السياق الحالي','Actualiser le contexte','Use current context'));self.refresh_button.clicked.connect(self.capture);layout.addWidget(self.refresh_button)
  for label,callback in [(t('حلّل بيانات الجلسة','Analyser la session','Analyze session data'),self.analyze),(t('ابحث عن مراجع','Rechercher des références','Find references'),lambda:self.search('brave')),(t('ابحث عن فيديو شرح','Rechercher une vidéo','Find an explanation video'),lambda:self.search('youtube'))]:
   button=action_button(label);button.clicked.connect(callback);layout.addWidget(button)
  self.tabs=QTabWidget();layout.addWidget(self.tabs,1)
  self.results=QTextBrowser();self.results.setOpenLinks(False);self.results.setOpenExternalLinks(False);self.results.anchorClicked.connect(self.open_source);self.tabs.addTab(self.results,t('النتائج','Résultats','Results'))
  self.cloud=Assistant(window);self.cloud.session_capture=self.capture;scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(self.cloud);self.tabs.addTab(scroll,t('تحليل سحابي','Analyse cloud','Cloud analysis'))
  self.timeline=QTextBrowser();self.timeline.setOpenLinks(False);self.timeline.anchorClicked.connect(self.open_source);self.tabs.addTab(self.timeline,t('سجل الجلسة','Journal','Session journal'))
  settings=QWidget();sl=QVBoxLayout(settings);info=QLabel(t('المفاتيح في ذاكرة الجلسة فقط. البحث يعرض مقتطفات؛ الفيديو يعرض وصفًا دون قراءة النص أو مشاهدة المحتوى.','Clés en mémoire. Extraits de recherche et descriptions vidéo uniquement.','Keys stay in session memory. Search returns excerpts; videos return descriptions, not transcripts or watched content.'));info.setWordWrap(True);sl.addWidget(info)
  self.keys={}
  for provider,title in [('brave','Brave Search API key'),('youtube','YouTube Data API key')]:
   field=QLineEdit(getattr(window,provider+'_key',''));field.setEchoMode(QLineEdit.Password);field.setPlaceholderText(title);field.setLayoutDirection(Qt.LeftToRight);field.textChanged.connect(lambda value,p=provider:setattr(window,p+'_key',value));sl.addWidget(field);self.keys[provider]=field
  self.external_consent=QCheckBox(t('أوافق على إرسال استعلام البحث المعروض فقط للخدمة','Autoriser l’envoi de la requête affichée','Approve sending only the displayed search query'));sl.addWidget(self.external_consent)
  self.query=QTextEdit();self.query.setMaximumHeight(110);sl.addWidget(self.query)
  self.cancel_button=action_button(t('إلغاء البحث','Annuler','Cancel search'));self.cancel_button.clicked.connect(self.cancel_search);sl.addWidget(self.cancel_button)
  browser=action_button(t('فتح البحث في المتصفح فقط','Recherche navigateur uniquement','Open browser search only'));browser.clicked.connect(self.browser_search);sl.addWidget(browser);sl.addStretch();self.tabs.addTab(settings,t('البحث والخصوصية','Recherche et confidentialité','Search and privacy'))
  self.feedback=QLabel();self.feedback.setWordWrap(True);layout.addWidget(self.feedback);self.tabs.currentChanged.connect(lambda index:self.refresh_history() if index==2 else None);self.capture()

 def capture(self):
  if self.search_task is not None or (getattr(self.window,'cloud_task',None) is not None and self.window.cloud_task.isRunning()):
   self.feedback.setText(t('انتظر الطلب أو ألغِه قبل تغيير السياق','Attendre ou annuler avant de changer le contexte','Wait or cancel before changing context'));return
  ws=getattr(self.window,'diagnostic_workspace',None);report=getattr(ws,'report',None);ecu=code=None;pids=[]
  if ws is not None:
   row=ws.dtc.currentRow() if ws.tabs.currentIndex()==1 and ws.dtc.selectedItems() else -1
   if row>=0 and ws.dtc.item(row,0) and ws.dtc.item(row,3):ecu=ws.dtc.item(row,0).text();code=ws.dtc.item(row,3).text()
   elif ws.ecus.currentData():ecu=ws.ecus.currentData()
   pids=ws.selected_pids()
  self.context=core.snapshot(report,getattr(self.window,'vehicle',{}),ecu,code,getattr(ws,'samples',()),pids,self.symptoms.toPlainText())
  self.sources=core.local_sources(self.context)
  for row in core.history(self.context['session_id']):
   if row['kind']=='search_results':self.sources+=row['payload'].get('results',[]);break
  self.cloud.attachment=self.context;self.cloud.approve.setChecked(False);self.cloud.approve.show();self.cloud.preview.setPlainText(json.dumps(self.context,ensure_ascii=False,indent=2));self.cloud.preview.show()
  bound=dict(self.context)
  self.cloud.on_complete=lambda value:core.record(bound['session_id'],'cloud_analysis',dict(value,context_fingerprint=bound['fingerprint']))
  vehicle=self.context['vehicle'];self.identity.setText(' · '.join([self.context['mode'].upper()]+[str(vehicle.get(k)) for k in ('make','model','year','engine') if vehicle.get(k)]+[self.context['ecu'],self.context['dtc']]))
  self.query.setPlainText(core.query_for(self.context).strip());self.render_sources();self.refresh_history()

 def events(self):return core.history(self.context['session_id'])
 def refresh_history(self):
  parts=[]
  for row in self.events():parts.append('<p><b>'+escape(row['kind'])+'</b> · '+escape(row['time'])+'<br>'+escape(json.dumps(row['payload'],ensure_ascii=False))+'</p>')
  self.timeline.setHtml(''.join(parts) or t('لا توجد أحداث للمساعد بعد','Aucun événement','No assistant events yet'))

 def analyze(self):
  c=self.context;data={'evidence':{'mode':c['mode'],'ecu':c['ecu'],'dtc':c['dtc'],'selected_samples':c['samples']},'interpretation':t('ملخص محلي للبيانات المسجلة؛ ليس استنتاجًا من نموذج ذكاء اصطناعي. رمز العطل وحده لا يثبت تلف قطعة.','Résumé local des données; pas une réponse IA. Un DTC ne prouve pas une pièce défectueuse.','Local summary of recorded data, not an AI inference. A DTC alone does not prove a defective part.'),'missing':[k for k in ('make','model','year','engine') if not c['vehicle'].get(k)],'next_test':t('حدد وحدة التحكم والأعراض، ثم راجع المرجع وإجراء الاختبار المطابق للسيارة قبل التنفيذ.','Identifier le calculateur et les symptômes puis consulter une procédure compatible.','Identify ECU and symptoms; consult a matching test procedure before execution.'),'sources':self.sources}
  core.record(c['session_id'],'local_analysis',data)
  parts=['<h3>'+t('الدليل المسجل','Observations','Recorded evidence')+'</h3><p>'+escape(' · '.join([c['mode'].upper(),c['ecu'],c['dtc']]))+'</p>']
  for sample in c['samples'][-5:]:parts.append('<p>'+escape(str(sample.get('ecu',''))+' · PID '+str(sample.get('pid',''))+' · '+str(sample.get('value','—'))+' '+str(sample.get('unit','')))+'<br>'+escape(str(sample.get('at','')) or t('لا يوجد توقيت مسجل','Horodatage absent','No recorded timestamp'))+'</p>')
  parts+=['<h3>'+t('التفسير','Interprétation','Interpretation')+'</h3><p>'+escape(data['interpretation'])+'</p>','<h3>'+t('الاختبار التالي','Prochain test','Next test')+'</h3><p>'+escape(data['next_test'])+'</p>','<h3>'+t('المعلومات الناقصة','Informations manquantes','Missing information')+'</h3><p>'+escape(' · '.join({'make':t('الماركة','Marque','Make'),'model':t('الموديل','Modèle','Model'),'year':t('السنة','Année','Year'),'engine':t('المحرك','Moteur','Engine')}.get(k,k) for k in data['missing']) or t('راجع هوية ECU وإصدارها','Vérifier la version ECU','Verify ECU identity and software'))+'</p>']
  for n,row in enumerate(self.sources,2):parts.append('<h3>[E'+str(n)+'] '+escape(row['title'])+'</h3><p>'+escape(row['text'])+'</p>')
  self.results.setHtml(''.join(parts));self.tabs.setCurrentIndex(0);self.refresh_history()
  self.cloud.prompt.setPlainText(t('حلّل الأدلة المرفقة. اعرض: الدليل، التفسير المحتمل، الاختبار التالي، المعلومات الناقصة والمصدر. لا تنفذ أي أمر.','Analyser les preuves: observations, hypothèses, prochain test, informations manquantes et sources. Aucune commande.','Analyze attached evidence: observations, hypotheses, next test, missing information and sources. Execute no commands.'))
  self.feedback.setText(t('لتحليل النموذج افتح «تحليل سحابي»، وأدخل المفتاح واعتمد معاينة البيانات ثم أرسل.','Pour l’IA: onglet cloud, clé, aperçu et consentement.','For model analysis: open Cloud analysis, enter key, approve preview and send.'))

 def render_sources(self):
  parts=[]
  for n,row in enumerate(self.sources,2):
   title=escape(row['title']);url=row.get('url','');link='<a href="'+escape(url,quote=True)+'">'+title+'</a>' if url else title
   parts.append('<p><b>[E'+str(n)+'] '+link+'</b><br>'+escape(row['content_type'])+' · '+escape(row['provider'])+'<br>'+escape(row['text'])+'</p>')
  self.results.setHtml(''.join(parts) or t('لا توجد مراجع مسترجعة لهذا السياق بعد','Aucune référence récupérée','No references retrieved for this context yet'))
  self.cloud.evidence_override=[{'id':'E1','type':'deidentified_session_snapshot','data':self.context}]+[{'id':'E'+str(i+2),'type':row['content_type'],'data':row} for i,row in enumerate(self.sources)]
  self.cloud.attachment=self.cloud.evidence_override;self.cloud.preview.setPlainText(json.dumps(self.cloud.attachment,ensure_ascii=False,indent=2));self.cloud.approve.setChecked(False)

 def search(self,provider):
  self.last_provider=provider;self.tabs.setCurrentIndex(0)
  if self.search_task is not None:self.feedback.setText(t('بحث جارٍ','Recherche en cours','Search in progress'));return
  key=self.keys[provider].text();query=self.query.toPlainText().strip()
  if not key or not self.external_consent.isChecked():
   self.render_sources();self.feedback.setText(t('المراجع المحلية جاهزة. البحث الخارجي يحتاج مفتاح الخدمة والموافقة في «البحث والخصوصية».','Références locales disponibles. Clé et consentement requis dans Recherche et confidentialité.','Local references available. External search needs a key and consent in Search and privacy.'));self.tabs.setCurrentIndex(3);return
  self.search_cancel=threading.Event();task=SearchTask(query,provider,key,True,self.search_cancel,self.window);self.search_task=task;self.window.assistant_search_task=task;self.window.assistant_search_cancel=self.search_cancel
  bound=dict(self.context)
  def result(rows):
   if self.search_cancel.is_set():return
   core.record(bound['session_id'],'search_results',{'query':query,'provider':provider,'results':rows,'context_fingerprint':bound['fingerprint']})
   if self.context['fingerprint']!=bound['fingerprint']:return
   self.sources=core.local_sources(bound)+rows;self.render_sources();self.refresh_history();self.feedback.setText(t('نتائج مسترجعة؛ مقتطفات وأوصاف فقط','Résultats: extraits et descriptions','Retrieved results: excerpts and descriptions only'))
  task.result.connect(result);task.failure.connect(self.feedback.setText)
  def finished():
   self.search_task=None;self.window.assistant_search_task=None;task.deleteLater()
  task.finished.connect(finished);self.feedback.setText(query);task.start()

 def cancel_search(self):
  if self.search_cancel:self.search_cancel.set()
 def open_source(self,url):
  try:value=core.safe_url(url.toString());opened=QDesktopServices.openUrl(QUrl(value))
  except ValueError as error:self.feedback.setText(str(error));return
  core.record(self.context['session_id'],'opened_source' if opened else 'source_open_failed',{'url':value,'note':self.symptoms.toPlainText()[:1200],'content_read':False});self.refresh_history()
  self.feedback.setText(t('المصدر في المتصفح؛ جلسة التشخيص محفوظة','Source dans le navigateur; session conservée','Source opened in browser; diagnostic session retained') if opened else t('تعذر فتح المتصفح','Navigateur indisponible','Browser could not be opened'))
 def browser_search(self):
  from urllib.parse import urlencode
  provider=getattr(self,'last_provider','brave');url=('https://www.youtube.com/results?' if provider=='youtube' else 'https://search.brave.com/search?')+urlencode({'search_query' if provider=='youtube' else 'q':self.query.toPlainText()})
  self.open_source(QUrl(url))
 def toggle_expanded(self):
  shell=self.window.professional_shell;self.expanded=not self.expanded
  if self.expanded:
   self.saved_sidebar=shell.sidebar.isVisible();self.saved_pages_max=self.window.pages.maximumWidth();shell.sidebar.hide();self.window.pages.setMaximumWidth(0);self.setMaximumWidth(16777215)
  else:
   self.window.pages.setMaximumWidth(self.saved_pages_max);shell.sidebar.setVisible(self.saved_sidebar);self.setMaximumWidth(540)
 def hideEvent(self,event):
  if self.expanded:self.toggle_expanded()
  self.cancel_search();self.cloud.cancel();super().hideEvent(event)
