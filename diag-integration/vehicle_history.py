"""Persistent vehicle identity and explicit workshop visits, separate from reconnects."""
import hashlib,json,uuid,datetime
import store

def schema(db):
 db.execute('CREATE TABLE IF NOT EXISTS vehicle_profiles(id TEXT PRIMARY KEY, vehicle TEXT NOT NULL, updated TEXT NOT NULL)')
 db.execute('CREATE TABLE IF NOT EXISTS vehicle_visits(id TEXT PRIMARY KEY, vehicle_id TEXT NOT NULL, opened TEXT NOT NULL, closed TEXT, notes TEXT NOT NULL DEFAULT "")')
def remember(vehicle):
 if not all(vehicle.get(k) for k in ('make','model','year')):raise ValueError('Vehicle identity incomplete')
 v=dict(vehicle);vin=str(v.get('vin') or '').strip().upper()
 if vin:
  if len(vin)!=17 or any(c not in '0123456789ABCDEFGHJKLMNPRSTUVWXYZ' for c in vin):raise ValueError('Invalid VIN')
  key='vin:'+vin
 else:
  key=str(v.get('_profile_id') or 'local:'+uuid.uuid4().hex);v['_profile_id']=key
 with store.db() as db:
  schema(db);db.execute('INSERT INTO vehicle_profiles VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET vehicle=excluded.vehicle,updated=excluded.updated',(key,json.dumps(v,ensure_ascii=False),datetime.datetime.now(datetime.timezone.utc).isoformat()))
 return key,v

def begin_visit(vehicle,resume=True):
 key,v=remember(vehicle)
 with store.db() as db:
  schema(db)
  if resume:
   row=db.execute('SELECT id FROM vehicle_visits WHERE vehicle_id=? AND closed IS NULL ORDER BY opened DESC LIMIT 1',(key,)).fetchone()
   if row:return row[0],v
  visit=uuid.uuid4().hex;db.execute('INSERT INTO vehicle_visits(id,vehicle_id,opened) VALUES(?,?,?)',(visit,key,datetime.datetime.now(datetime.timezone.utc).isoformat()))
 return visit,v

def profiles():
 with store.db() as db:
  schema(db);rows=db.execute('SELECT p.id,p.vehicle,COUNT(v.id),MAX(v.opened) FROM vehicle_profiles p LEFT JOIN vehicle_visits v ON p.id=v.vehicle_id GROUP BY p.id ORDER BY p.updated DESC LIMIT 100').fetchall()
 return [dict(id=i,vehicle=json.loads(raw),visits=count,last_visit=last) for i,raw,count,last in rows]
