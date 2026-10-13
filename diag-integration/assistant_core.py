"""Read-only session snapshots, durable assistant journal and bounded search APIs.

No adapter imports and no vehicle commands. Search excerpts are untrusted evidence.
"""
import copy, datetime, hashlib, ipaddress, json, re, sqlite3
import urllib.request, urllib.error, urllib.parse
from pathlib import Path

def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()

def redact(value):
 from ai_workspace import sanitized_scan
 return sanitized_scan(value)

def snapshot(report, vehicle=None, ecu=None, dtc=None, samples=(), pids=(), symptoms=''):
 observed=report if isinstance(report,dict) else {}
 identity=observed.get('id') or 'offline-'+hashlib.sha256(json.dumps(vehicle or {},sort_keys=True,default=str).encode()).hexdigest()[:24]
 data=redact(observed)
 if ecu and isinstance(data.get('ecus'),list):data['ecus']=[row for row in data['ecus'] if row.get('id')==ecu]
 selected=[redact(dict(r)) for r in samples if (not ecu or r.get('ecu')==ecu) and (not pids or r.get('pid') in pids)][-30:]
 mode=observed.get('evidence') or 'offline'
 result={'session_id':str(identity),'mode':mode,'vehicle':redact(observed.get('vehicle',vehicle or {})),
         'ecu':str(ecu or ''),'dtc':dtc if re.fullmatch(r'[PBCU][0-9A-F]{4}',str(dtc or ''),re.I) else '',
         'report':data,'samples':selected,'symptoms':redact({'value':str(symptoms)[:1200]})['value']}
 # Remove identities that occur in free-text notes as well as structured fields.
 for source in (observed.get('vehicle',{}),vehicle or {}):
  for name in ('vin','phone','email','plate','client','customer'):
   val=source.get(name)
   if isinstance(val,str) and val:result['symptoms']=result['symptoms'].replace(val,'[redacted]')
 if len(json.dumps(result,ensure_ascii=False))>20000:
  result['report']={k:data[k] for k in ('status','evidence','protocol','vehicle') if k in data};result['report_truncated']=True
 result['fingerprint']=hashlib.sha256(json.dumps(result,sort_keys=True,ensure_ascii=False,default=str).encode()).hexdigest()
 return copy.deepcopy(result)

def journal(path=None):
 if path is None:
  import store
  path=store.BASE/'workshop.db'
 con=sqlite3.connect(path)
 con.execute('CREATE TABLE IF NOT EXISTS assistant_events(id INTEGER PRIMARY KEY,session_id TEXT NOT NULL,time TEXT NOT NULL,kind TEXT NOT NULL,payload TEXT NOT NULL)')
 return con

def record(session_id,kind,payload,path=None):
 encoded=json.dumps(payload,ensure_ascii=False)
 if len(encoded)>100000:raise ValueError('Assistant event too large')
 with journal(path) as con:con.execute('INSERT INTO assistant_events(session_id,time,kind,payload) VALUES(?,?,?,?)',(str(session_id),now(),str(kind),encoded))

def history(session_id,path=None):
 with journal(path) as con:
  return [{'id':i,'time':t,'kind':k,'payload':json.loads(p)} for i,t,k,p in con.execute('SELECT id,time,kind,payload FROM assistant_events WHERE session_id=? ORDER BY id DESC LIMIT 100',(str(session_id),))]

def safe_url(value):
 if not isinstance(value,str) or len(value)>4096 or any(ord(c)<33 for c in value):raise ValueError('Invalid source URL')
 u=urllib.parse.urlsplit(value)
 if u.scheme not in ('http','https') or not u.hostname or u.username or u.password:raise ValueError('Only public HTTP(S) sources allowed')
 host=u.hostname.lower().rstrip('.')
 if host=='localhost' or host.endswith(('.localhost','.local')) or '.' not in host:raise ValueError('Local source blocked')
 try:
  if not ipaddress.ip_address(host).is_global:raise ValueError('Private source blocked')
 except ValueError:
  if re.fullmatch(r'[0-9.:]+',host):raise ValueError('Private or invalid address blocked')
 if u.port not in (None,80,443):raise ValueError('Nonstandard port blocked')
 if any(k.casefold() in ('key','api_key','apikey','token','access_token','authorization') for k,v in urllib.parse.parse_qsl(u.query)):raise ValueError('Secret-bearing source blocked')
 return value

def query_for(context):
 v=context['vehicle'];return ' '.join(str(v.get(k) or '') for k in ('make','model','year','engine'))+' '+context.get('dtc','')+' '+context.get('symptoms','')

def local_sources(context):
 rows=[];code=context.get('dtc')
 if code:
  import automotive_data
  value=automotive_data.dtc(code,context['vehicle'].get('make',''))
  definitions=value.get('definitions',[]) if isinstance(value,dict) else []
  text='\n\n'.join(str(row.get('description') or row.get('definition') or '')+'\n'+str(row.get('source') or '')+' · '+str(row.get('applicability') or '') for row in definitions[:5])
  rows.append({'title':code,'text':text or 'No local definition available for this code','content_type':'local_dtc_definition','provider':'GITM local','url':'','retrieved_at':now()})
 return rows

class FixedEndpointRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):raise ValueError('Search endpoint redirect refused')

def request_json(request,cancel):
 if cancel.is_set():return {}
 try:
  with urllib.request.build_opener(FixedEndpointRedirect()).open(request,timeout=15) as response:raw=response.read(1024*1024+1)
 except urllib.error.HTTPError as e:raise ValueError('Search service HTTP '+str(e.code)) from None
 except urllib.error.URLError:raise ValueError('Search service unavailable; local references remain available') from None
 if cancel.is_set():return {}
 if len(raw)>1024*1024:raise ValueError('Search response too large')
 result=json.loads(raw)
 if not isinstance(result,dict):raise ValueError('Invalid search response')
 return result

def search_external(query,provider,key,consent,cancel):
 if not consent:raise ValueError('External search consent required')
 if not key:raise ValueError('Search API key is not configured')
 if not query.strip() or len(query)>1800:raise ValueError('Search query missing or too large')
 if cancel.is_set():return []
 if provider=='brave':
  request=urllib.request.Request('https://api.search.brave.com/res/v1/web/search?'+urllib.parse.urlencode({'q':query,'count':8,'extra_snippets':'true'}),headers={'Accept':'application/json','X-Subscription-Token':key})
 elif provider=='youtube':
  request=urllib.request.Request('https://www.googleapis.com/youtube/v3/search?'+urllib.parse.urlencode({'part':'snippet','type':'video','maxResults':8,'q':query,'key':key}),headers={'Accept':'application/json'})
 else:raise ValueError('Unknown search provider')
 raw=request_json(request,cancel);rows=[]
 for item in (raw.get('web',{}).get('results',[]) if provider=='brave' else raw.get('items',[]))[:8]:
  if not isinstance(item,dict):continue
  if provider=='youtube':
   video=item.get('id',{}).get('videoId','')
   if not re.fullmatch(r'[A-Za-z0-9_-]{11}',video):continue
   info=item.get('snippet',{});url='https://www.youtube.com/watch?v='+video;text=info.get('description','');title=info.get('title','')
  else:url=item.get('url','');text=item.get('description','');title=item.get('title','')
  try:url=safe_url(url)
  except (ValueError,TypeError):continue
  rows.append({'title':str(title)[:250],'text':str(text)[:2000],'url':url,'provider':provider,'retrieved_at':now(),
               'content_type':'search_snippet' if provider=='brave' else 'video_description','transcript_read':False})
 return rows
