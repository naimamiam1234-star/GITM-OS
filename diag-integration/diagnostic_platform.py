"""Diagnostic definition registry. Imported claims never grant vehicle-test status."""
import json,hashlib,re,time
import store,ecu_scan
from transport import LINK
KINDS={'22':'READ','19':'READ','2E':'WRITE','2F':'ACTUATOR','31':'ROUTINE','11':'RESET','14':'CLEAR_DTC','27':'SECURITY_ACCESS','10':'SESSION'}
def hexbytes(value):
 if not isinstance(value,str):raise ValueError('Hex string required')
 value=re.sub(r'\s+','',value).upper()
 if not re.fullmatch(r'(?:[0-9A-F]{2}){1,256}',value):raise ValueError('Invalid diagnostic bytes')
 return value

def db():
 c=store.db();c.execute('CREATE TABLE IF NOT EXISTS diagnostic_models(id TEXT PRIMARY KEY,model TEXT)');return c

def import_ddt(data,vehicle,source,persist=True):
 if not isinstance(data,dict) or not isinstance(source,str) or not 8<=len(source)<=500:raise ValueError('Documented source required')
 if not isinstance(vehicle,dict) or not all(vehicle.get(k) for k in ['make','model','engine','year']):raise ValueError('Exact vehicle and engine required')
 year=int(vehicle['year'])
 if not 1900<=year<=2100:raise ValueError('Invalid year')
 obd=data.get('obd',{});actions=[]
 requests=data.get('requests',[])
 if not isinstance(requests,list) or not 1<=len(requests)<=300:raise ValueError('DDT JSON requests list required (1–300)')
 for r in requests:
  request=hexbytes(r.get('sentbytes'));reply=r.get('replybytes','');reply=hexbytes(reply) if reply else None
  kind=KINDS.get(request[:2],'UNKNOWN')
  actions.append({'name':str(r.get('name',''))[:100],'kind':kind,'request':request,'positive_response':reply,'input_parameters':r.get('sendbyte_dataitems',{}),'output_parameters':r.get('receivebyte_dataitems',{}),'denied_sessions':r.get('deny_sds',[]),'minbytes':r.get('minbytes',0),'shiftbytescount':r.get('shiftbytescount',0),'manualsend':bool(r.get('manualsend',False)),'verification_level':1,'verification_scope':'definition_import_only','runtime_supported':kind=='READ' and (bool(re.fullmatch('22[0-9A-F]{4}',request)) or request=='1902FF') and not r.get('sendbyte_dataitems') and not r.get('manualsend') and not r.get('shiftbytescount') and not r.get('deny_sds')})
 model={'format':'gitm-diagnostic-model/1','vehicle':{**vehicle,'year':year},'ecu':str(data.get('ecuname','Unknown'))[:100],'transport':obd,'identities':data.get('autoidents',[]),'parameters':data.get('data',{}),'endian':data.get('endian','Big'),'source':source,'importer':'ddt-supported-subset/2','source_format':data.get('_source_format','DDT_JSON_SUBSET'),'source_sha256':hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest(),'actions':actions,'hardware_tested':False}
 payload=json.dumps(model,sort_keys=True)
 if len(payload.encode())>60000:raise ValueError('Converted model too large')
 key=hashlib.sha256(payload.encode()).hexdigest()
 if persist:
  with db() as c:c.execute('INSERT OR IGNORE INTO diagnostic_models VALUES(?,?)',(key,payload))
 return {'id':key,**model}

def get(key):
 with db() as c:row=c.execute('SELECT model FROM diagnostic_models WHERE id=?',(str(key),)).fetchone()
 if not row:raise ValueError('Model not found')
 return json.loads(row[0])

def listing():
 with db() as c:rows=c.execute('SELECT id,model FROM diagnostic_models').fetchall()
 return [{'id':k,**json.loads(p)} for k,p in rows]

def preview(key,index,response=None):
 m=get(key)
 if type(index)!=int or not 0<=index<len(m['actions']):raise ValueError('Invalid action index')
 a=m['actions'][index];out={'action':a,'source':m['source'],'ecu':m['ecu'],'transport':m['transport'],'sent_to_vehicle':False,'vehicle_tested':False}
 if response is not None:
  raw=hexbytes(response)
  if raw.startswith('7F'+a['request'][:2]) and len(raw)==6:out['response']={'status':'negative','nrc':raw[4:]}
  elif a['positive_response'] and raw.startswith(a['positive_response']):out['response']={'status':'positive_prefix_only','payload':raw,'full_parameter_decode':False}
  else:raise ValueError('Response does not match diagnostic definition')
  if out['response']['status']=='positive_prefix_only' and a['output_parameters']:
   from core.vehiclepacks.importers.ddt.xml_reader import decode
   out['response']['values']=decode(m,a,raw)
   out['response']['status']='decoded_supported_subset'
   out['response']['full_parameter_decode']=True
 return out

def execute_read(key,index,vehicle,expected_sw):
 m=get(key);a=preview(key,index)['action'];obd=m['transport']
 if vehicle!=m['vehicle']:raise ValueError('Selected vehicle must exactly match imported vehicle')
 if not a['runtime_supported']:raise ValueError('Action not supported by this read-only runtime')
 return execute_can_read(m,vehicle,expected_sw,a['request'],obd,{'model':key,'index':index})

def execute_can_read(m,vehicle,expected_sw,request,obd,provenance):
 if vehicle!=m['vehicle']:raise ValueError('Selected vehicle must exactly match imported vehicle')
 request=hexbytes(request)
 if not re.fullmatch('22[0-9A-F]{4}',request) and request!='1902FF':raise ValueError('Only a single read DID or DTC status read is allowed')
 expected_sw=hexbytes(expected_sw)
 if obd.get('protocol')!='CAN' or obd.get('baudrate') not in (250000,500000):raise ValueError('CAN 250/500 kbit/s required')
 protocol=6 if obd['baudrate']==500000 else 8
 tx=obd.get('send_id','').upper();rx=obd.get('recv_id','').upper()
 p={'format':'gitm-ecu-profile/1','validated':True,'source':m['source'],'vehicle':{'make':vehicle['make'],'model':vehicle['model'],'engine':vehicle['engine'],'years':[vehicle['year']]},'bus':{'type':'hs-can','protocol':protocol},'ecus':[{'name':m['ecu'],'tx_id':tx,'rx_id':rx,'reads':['vin']}]}
 ecu_scan.validate_profile(p)
 with LINK.lock:
  if LINK.family!='elm' or LINK.protocol!=protocol:raise ValueError('Discover matching ELM CAN protocol first')
  try:
   for cmd in ['ATH0','ATCAF1','ATCFC1','ATAL','ATSH'+tx,'ATCRA'+rx,'ATFCSH'+tx,'ATFCSD300005','ATFCSM1']:ecu_scan.at(cmd)
   identity=ecu_scan.uds_payload(LINK.query('22F189'),'22F189')
   if identity.get('hex')!=expected_sw:raise ValueError('ECU software identity mismatch; action was not sent')
   result=ecu_scan.uds_payload(LINK.query(request),request)
   store.save(vehicle,'DIAGNOSTIC_ACTION',{**provenance,'source':m['source'],'expected_sw':expected_sw,'request':request,'result':result})
   return {'result':result,'ecu_sw_hex':expected_sw,'sent_to_vehicle':True,'action_kind':'READ','verification_level_unchanged':1}
  finally:
   ecu_scan.restore_adapter()
