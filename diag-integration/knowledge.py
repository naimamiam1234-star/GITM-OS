"""Vehicle-scoped technical evidence; catalogue entries alone are not evidence."""
import json,hashlib,datetime
import store

def import_document(data):
    for key in ('source','license','version','date','language','text'):
        if not isinstance(data.get(key),str) or not data[key].strip():raise ValueError('Missing '+key)
    if not isinstance(data.get('vehicle'),dict) or not all(data['vehicle'].get(k) for k in ('make','model','year')):raise ValueError('Exact vehicle required')
    if len(data['text'])>100000:raise ValueError('Document exceeds 100000 characters')
    clean={k:data[k] for k in ('source','license','version','date','language','text','vehicle')}
    clean['kind']=data.get('kind','technical_information');clean['ecu_hw']=data.get('ecu_hw','');clean['ecu_sw']=data.get('ecu_sw','');clean['verification']='IMPORTED_UNVERIFIED'
    clean['sha256']=hashlib.sha256(json.dumps(clean,sort_keys=True).encode()).hexdigest()
    with store.db() as c:
        c.execute('CREATE TABLE IF NOT EXISTS technical_evidence(id TEXT PRIMARY KEY,payload TEXT)')
        c.execute('INSERT OR REPLACE INTO technical_evidence VALUES(?,?)',(clean['sha256'],json.dumps(clean,ensure_ascii=False)))
    return {'id':clean['sha256'],'verification':clean['verification']}

def evidence(vehicle):
    if not all(vehicle.get(k) for k in ('make','model','year')):return []
    with store.db() as c:
        c.execute('CREATE TABLE IF NOT EXISTS technical_evidence(id TEXT PRIMARY KEY,payload TEXT)');rows=c.execute('SELECT payload FROM technical_evidence ORDER BY rowid DESC LIMIT 500').fetchall()
    selected=[]
    for (raw,) in rows:
        row=json.loads(raw)
        if any(str(row['vehicle'].get(k,'')).casefold()!=str(vehicle.get(k,'')).casefold() for k in ('make','model','year')):continue
        if any(row['vehicle'].get(k) and str(row['vehicle'][k]).strip().casefold()!=str(vehicle.get(k,'')).strip().casefold() for k in ('engine','fuel','market','generation')):continue
        if row.get('ecu_hw') and row['ecu_hw']!=vehicle.get('ecu_hw'):continue
        if row.get('ecu_sw') and row['ecu_sw']!=vehicle.get('ecu_sw'):continue
        row['text']=row['text'][:4000];row['id']='E'+str(len(selected)+1);selected.append(row)
        if len(selected)==4:break
    return selected
