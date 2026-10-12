"""Read-only discovery. Generic replies never imply a manufacturer ECU role."""
import re,time,math
from transport import LINK
from diagnostics import read
READS={'part_number':'22F187','vin':'22F190','serial_number':'22F18C','dtc':'1902FF'}

def obd_responders(raw, width):
 found={}
 for line in raw.upper().replace('\r','\n').splitlines():
  compact=re.sub(r'\s+','',line)
  n=3 if width==11 else 8
  if not re.fullmatch(r'[0-9A-F]+',compact) or len(compact)<n+14:continue
  address=int(compact[:n],16)
  if width==11 and not 0x7E8<=address<=0x7EF:continue
  if width==29 and address&0x1FFFFF00!=0x18DAF100:continue
  try:data=bytes.fromhex(compact[n:])
  except ValueError:continue
  # Headers on, automatic formatting on: CAN PCI is retained on single frames.
  if len(data)<7 or data[0]!=6 or data[1:3]!=b'\x41\x00':continue
  tx=address-8 if width==11 else 0x18DA00F1|((address&255)<<8)
  found[address]={'name':f'OBD ECU {address:0{n}X}','role':'unknown','rx_id':f'{address:0{n}X}','tx_id':f'{tx:0{n}X}','status':'responded','supported_pid_bitmap':data[3:7].hex().upper()}
 return list(found.values())

def discover():
 with LINK.lock:
  if not LINK.family:LINK.discover()
  if not LINK.family:raise ConnectionError('No compatible adapter connected; pair wireless adapters first')
  if LINK.family=='gitm':
   raw=LINK.query('SCAN')
   if not raw.startswith('ECUS='):raise ValueError('Update STM32 firmware for ECU discovery')
   units=[]
   for value in raw[5:].split(','):
    if re.fullmatch(r'7E[8-F]',value):units.append({'name':'OBD ECU '+value,'role':'unknown','rx_id':value,'tx_id':f'{int(value,16)-8:03X}','status':'responded'})
   protocol=6
  else:
   LINK.query('0100');number=LINK.query('ATDPN').strip().upper().removeprefix('A')
   if not re.fullmatch('[1-9]',number):raise ValueError('Unrecognized established protocol')
   protocol=int(number);units=[]
   if protocol in (6,7,8,9):
    try:
     at('ATH1');raw=LINK.query('0100');units=obd_responders(raw,11 if protocol in (6,8) else 29)
    finally:at('ATH0')
  LINK.protocol=protocol
  out={'adapter':LINK.info(),'units':units,'coverage':'Generic OBD responders only; ECU roles require a vehicle profile','errors':{}}
  for command,key in [('VIN','vin'),('DTC','emissions_dtc')]:
   try:out[key]=read(command)
   except (ValueError,RuntimeError,TimeoutError) as e:out['errors'][key]=str(e)
  return out

def validate_profile(p):
 if not isinstance(p,dict) or p.get('format')!='gitm-ecu-profile/1':raise ValueError('Invalid profile format')
 if p.get('validated') is not True or not isinstance(p.get('source'),str) or len(p['source'].strip())<8:raise ValueError('Profile must declare documented, tested addresses and its source')
 v=p.get('vehicle',{})
 if not isinstance(v,dict) or not all(isinstance(v.get(k),str) and v[k].strip() for k in ('make','model')):raise ValueError('Exact make/model required')
 years=v.get('years')
 if not isinstance(years,list) or not years or len(years)>100 or any(type(y)!=int or not 1900<=y<=2100 for y in years):raise ValueError('Explicit model years required')
 bus=p.get('bus',{})
 if bus not in ({'type':'hs-can','protocol':6},{'type':'hs-can','protocol':7},{'type':'hs-can','protocol':8},{'type':'hs-can','protocol':9}):raise ValueError('Runtime profiles currently support high-speed CAN OBD protocols 6–9 only')
 units=p.get('ecus');seen=set();width=11 if bus['protocol'] in (6,8) else 29
 if not isinstance(units,list) or not 1<=len(units)<=64:raise ValueError('Profile requires 1–64 ECUs')
 for u in units:
  if not isinstance(u,dict) or not isinstance(u.get('name'),str) or not 1<=len(u['name'])<=80:raise ValueError('Invalid ECU name')
  addresses=[]
  for k in ('tx_id','rx_id'):
   value=u.get(k)
   if not isinstance(value,str) or not re.fullmatch('[0-9A-Fa-f]{3}' if width==11 else '[0-9A-Fa-f]{8}',value):raise ValueError('CAN address width mismatch')
   a=int(value,16)
   if not 0<a<(1<<width) or width==11 and a==0x7DF or width==29 and a&0x1FFF0000==0x18DB0000:raise ValueError('Physical unicast address required')
   addresses.append(a)
  if addresses[0]==addresses[1] or tuple(addresses) in seen:raise ValueError('Duplicate or identical ECU addresses')
  seen.add(tuple(addresses))
  if not isinstance(u.get('reads'),list) or not u['reads'] or any(x not in READS for x in u['reads']):raise ValueError('Only declared identification and DTC read operations allowed')
  live=u.get('live_data',[])
  if not isinstance(live,list) or len(live)>16:raise ValueError('Maximum 16 DID definitions per ECU')
  names=set()
  for x in live:
   if not isinstance(x,dict) or not isinstance(x.get('name'),str) or not 1<=len(x['name'])<=60 or x['name'] in names:raise ValueError('Unique DID names required')
   names.add(x['name'])
   if not isinstance(x.get('did'),str) or not re.fullmatch('[0-9A-Fa-f]{4}',x['did']):raise ValueError('DID requires 4 hex digits')
   if type(x.get('offset',0))!=int or not 0<=x.get('offset',0)<=256 or type(x.get('length'))!=int or not 1<=x['length']<=8:raise ValueError('Invalid DID byte range')
   if x.get('endian','big') not in ('big','little') or type(x.get('signed',False))!=bool:raise ValueError('Invalid DID encoding')
   if not isinstance(x.get('unit',''),str) or len(x.get('unit',''))>24:raise ValueError('Invalid unit')
   for k,default in [('scale',1),('bias',0)]:
    v=x.get(k,default)
    if type(v) not in (int,float) or not math.isfinite(v) or abs(v)>1e9:raise ValueError('Invalid DID scaling')
 return p

def decode_live(value,definition):
 if value['status']!='responded':return value
 data=bytes.fromhex(value['hex']);start=definition.get('offset',0);end=start+definition['length']
 if len(data)<end:raise ValueError('DID response shorter than documented byte range')
 n=int.from_bytes(data[start:end],definition.get('endian','big'),signed=definition.get('signed',False))
 return {**value,'value':n*definition.get('scale',1)+definition.get('bias',0),'unit':definition.get('unit',''),'sample_time':time.time()}

def uds_payload(raw,request):
 request=re.sub(r'\s+','',request).upper()
 if not re.fullmatch(r'22[0-9A-F]{4}|1902FF',request):raise ValueError('Unsupported UDS read request')
 lines=[]
 for line in raw.upper().replace('\r','\n').splitlines():
  if re.match(r'^\s*\d+:',line):line=line.split(':',1)[1]
  s=re.sub(r'\s+','',line)
  if s==request:continue # Adapter command echo is not ECU payload.
  # ELM's standalone ISO-TP length (three hex digits) is not payload.
  if re.fullmatch('[0-9A-F]+',s) and len(s)%2==0:
   lines.append(bytes.fromhex(s))
 data=b''.join(lines);sid=int(request[:2],16);positive=bytes([sid+0x40])
 # Consume pending notifications only when a final response is already present.
 # This parser does not wait for a later transport packet or implement P2*.
 while data.startswith(bytes([0x7f,sid,0x78])) and len(data)>3:data=data[3:]
 if data.startswith(b'\x7f'):
  if len(data)!=3 or data[1]!=sid:raise ValueError('Malformed UDS negative response')
  return {'status':'responded_pending' if data[2]==0x78 else 'responded_negative','nrc':f'{data[2]:02X}','raw':raw}
 if not data.startswith(positive):raise ValueError('Unexpected UDS response')
 if request.startswith('22'):
  if data[1:3]!=bytes.fromhex(request[2:]):raise ValueError('DID response mismatch')
  if len(data)==3:raise ValueError('Empty DID response')
  if request=='22F190' and not re.fullmatch(rb'[A-HJ-NPR-Z0-9]{17}',data[3:]):raise ValueError('Invalid VIN DID response')
  return {'status':'responded','hex':data[3:].hex().upper(),'text':data[3:].decode('ascii',errors='replace'),'raw':raw}
 if len(data)<3 or data[1]!=2 or (len(data)-3)%4:raise ValueError('Malformed DTC response')
 return {'status':'responded','status_availability':f'{data[2]:02X}','dtcs':[{'uds_code':data[i:i+3].hex().upper(),'status':f'{data[i+3]:02X}'} for i in range(3,len(data),4)],'raw':raw}

def at(command):
 if LINK.query(command).strip().upper()!='OK':raise ValueError('Adapter does not support '+command)

def restore_adapter():
 """Restore a known ELM configuration; fail closed if reconnection fails."""
 kind,target,baud=LINK.kind,LINK.target,getattr(LINK,'baud',115200)
 try:
  at('ATD');LINK.connect(kind,target,baud,'elm')
 except Exception as e:
  LINK.close();raise ConnectionError('Adapter defaults could not be restored; disconnected') from e

def scan_profile(profile,vehicle,ecu_index=None,live_only=False):
 if type(live_only)!=bool:raise ValueError('live_only must be boolean')
 p=validate_profile(profile);v=p['vehicle']
 if not isinstance(vehicle,dict) or any(str(vehicle.get(k,vehicle.get(k.title(),''))).casefold()!=v[k].casefold() for k in ('make','model')) or int(vehicle.get('year',vehicle.get('ModelYear',0))) not in v['years']:raise ValueError('Profile does not match the selected vehicle/year')
 if v.get('engine') and vehicle.get('engine')!=v['engine']:raise ValueError('Engine must match profile exactly')
 if ecu_index is not None:
  if type(ecu_index)!=int or not 0<=ecu_index<len(p['ecus']):raise ValueError('Invalid ECU selection')
  selected=[p['ecus'][ecu_index]]
 else:selected=p['ecus']
 if live_only and ecu_index is None:raise ValueError('Select one ECU for live data')
 with LINK.lock:
  if LINK.family!='elm':raise ValueError('Addressed UDS profile scan currently requires a compatible ELM327/STN CAN adapter')
  if LINK.protocol!=p['bus']['protocol']:raise ValueError('Run automatic discovery first; established CAN protocol must match profile')
  results=[];deadline=time.monotonic()+90
  try:
   at('ATH0');at('ATCAF1');at('ATCFC1');at('ATAL')
   for u in selected:
    if time.monotonic()>=deadline:
     results.append({'name':u['name'],'rx_id':u['rx_id'],'status':'not_attempted','reason':'90-second scan budget exhausted'});continue
    item={'name':u['name'],'role':u.get('role','unknown'),'tx_id':u['tx_id'],'rx_id':u['rx_id'],'reads':{},'status':'no_valid_response'};results.append(item)
    try:
     tx=u['tx_id'].upper();at('ATSH'+tx);at('ATCRA'+u['rx_id'].upper())
     # Explicit flow-control address; never derive manufacturer physical addresses.
     at('ATFCSH'+tx);at('ATFCSD300005');at('ATFCSM1')
     definitions={x['name']:x for x in u.get('live_data',[])} if live_only else {}
     operations={name:'22'+x['did'].upper() for name,x in definitions.items()} if live_only else {key:READS[key] for key in u['reads']}
     if live_only and not operations:raise ValueError('No documented live DIDs in this ECU profile')
     for key,request in operations.items():
      if time.monotonic()>=deadline:
       item['reads'][key]={'error':'Scan time budget exhausted'};continue
      try:
       value=uds_payload(LINK.query(request),request)
       if live_only:value=decode_live(value,definitions[key])
       item['reads'][key]=value
       item['status']='responded' if value['status']=='responded' or item['status']=='responded' else value['status']
      except (ValueError,RuntimeError,TimeoutError) as e:item['reads'][key]={'error':str(e)}
    except (ValueError,RuntimeError,TimeoutError) as e:item['error']=str(e)
  finally:
   # Restore adapter defaults; reconnect establishes a fresh known configuration.
   restore_adapter()
  return {'units':results,'profile_source':p['source'],'validation':'Declared by profile author; not independently certified by GITM','coverage':'Only these declared physical addresses were queried'}
