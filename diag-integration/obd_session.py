"""Measured, per-responder CAN OBD sessions. No OEM write/flash dispatch."""
import contextlib, datetime, re, threading, uuid, time
from transport import LINK

def stamp(): return datetime.datetime.now(datetime.timezone.utc).isoformat()

def parse_can(raw, protocol):
    """ELM ATH1 / D0 / CAF1 frames, including independently interleaved ISO-TP."""
    if protocol not in (6,7,8,9): raise ValueError('CAN OBD protocols 6–9 required')
    width=3 if protocol in (6,8) else 8
    complete={}; pending={}
    for line in raw.upper().replace('\r','\n').splitlines():
        s=re.sub(r'\s+','',line)
        if not s or s in ('SEARCHING...','BUSINIT...OK'): continue
        if not re.fullmatch('[0-9A-F]+',s) or len(s)<width+4 or (len(s)-width)%2:
            raise ValueError('Malformed or headerless CAN response: '+line[:100])
        ecu=s[:width]; address=int(ecu,16)
        if width==3 and not 0x7E8<=address<=0x7EF: raise ValueError('Unexpected OBD responder '+ecu)
        if width==8 and address&0x1FFFFF00!=0x18DAF100: raise ValueError('Unexpected OBD responder '+ecu)
        frame=bytes.fromhex(s[width:]);kind=frame[0]>>4
        if len(frame)>8: raise ValueError('CAN frame exceeds eight bytes')
        if kind==0:
            n=frame[0]&15
            if not 1<=n<=7 or len(frame)<n+1 or ecu in pending or ecu in complete:
                raise ValueError('Invalid or duplicate single frame '+ecu)
            complete[ecu]=frame[1:n+1]
        elif kind==1:
            if len(frame)!=8 or ecu in pending or ecu in complete: raise ValueError('Invalid first frame '+ecu)
            n=((frame[0]&15)<<8)|frame[1]
            if not 8<=n<=4095: raise ValueError('Invalid ISO-TP length')
            pending[ecu]=[n,bytearray(frame[2:]),1]
        elif kind==2:
            if ecu not in pending: raise ValueError('Orphan continuation '+ecu)
            n,data,seq=pending[ecu]
            if frame[0]&15!=seq: raise ValueError('ISO-TP sequence mismatch '+ecu)
            needed=n-len(data)
            if len(frame)-1<min(7,needed): raise ValueError('Short continuation '+ecu)
            data.extend(frame[1:]);pending[ecu][2]=(seq+1)&15
            if len(data)>=n:complete[ecu]=bytes(data[:n]);del pending[ecu]
        else:raise ValueError('Unexpected CAN PCI '+ecu)
    if pending:raise ValueError('Incomplete ISO-TP response: '+', '.join(pending))
    if not complete:raise ValueError('No valid ECU responses')
    return complete

# Standard generic PID definitions, restricted to measured supported PIDs.
# Formulas documented by SAE J1979 implementations; see SOURCES.md.
PIDS={
 0x04:('Calculated load','%',1,lambda d:d[0]*100/255),
 0x05:('Coolant','°C',1,lambda d:d[0]-40),
 0x06:('Short fuel trim B1','%',1,lambda d:(d[0]-128)*100/128),
 0x07:('Long fuel trim B1','%',1,lambda d:(d[0]-128)*100/128),
 0x08:('Short fuel trim B2','%',1,lambda d:(d[0]-128)*100/128),
 0x09:('Long fuel trim B2','%',1,lambda d:(d[0]-128)*100/128),
 0x0A:('Fuel pressure','kPa',1,lambda d:d[0]*3),
 0x0B:('Intake manifold pressure','kPa',1,lambda d:d[0]),
 0x0C:('Engine speed','rpm',2,lambda d:int.from_bytes(d[:2],'big')/4),
 0x0D:('Vehicle speed','km/h',1,lambda d:d[0]),
 0x0E:('Timing advance','°',1,lambda d:d[0]/2-64),
 0x0F:('Intake air','°C',1,lambda d:d[0]-40),
 0x10:('Mass air flow','g/s',2,lambda d:int.from_bytes(d[:2],'big')/100),
 0x11:('Throttle','%',1,lambda d:d[0]*100/255),
 0x1F:('Engine run time','s',2,lambda d:int.from_bytes(d[:2],'big')),
 0x21:('Distance with MIL','km',2,lambda d:int.from_bytes(d[:2],'big')),
 0x2F:('Fuel level','%',1,lambda d:d[0]*100/255),
 0x31:('Distance since clear','km',2,lambda d:int.from_bytes(d[:2],'big')),
 0x33:('Barometric pressure','kPa',1,lambda d:d[0]),
 0x42:('Control module voltage','V',2,lambda d:int.from_bytes(d[:2],'big')/1000),
 0x43:('Absolute load','%',2,lambda d:int.from_bytes(d[:2],'big')*100/255),
 0x44:('Commanded equivalence ratio','ratio',2,lambda d:int.from_bytes(d[:2],'big')/32768),
 0x46:('Ambient air','°C',1,lambda d:d[0]-40),
 0x49:('Accelerator position D','%',1,lambda d:d[0]*100/255),
 0x4A:('Accelerator position E','%',1,lambda d:d[0]*100/255),
 0x5C:('Engine oil','°C',1,lambda d:d[0]-40),
 0x5E:('Engine fuel rate','L/h',2,lambda d:int.from_bytes(d[:2],'big')/20),
}
def decode_pid(pid,data):
    if pid not in PIDS:raise ValueError('PID decoder unavailable')
    name,unit,size,decode=PIDS[pid]
    if len(data)!=size:raise ValueError('PID data length mismatch')
    return {'pid':pid,'name':name,'value':round(decode(data),4),'unit':unit}

def readiness(data):
    if len(data)!=4:raise ValueError('Readiness requires four bytes')
    a,b,c,d=data; diesel=bool(b&8)
    monitors=[{'name':name,'supported':bool(b&(1<<i)),'complete':not bool(b&(1<<(i+4)))} for i,name in enumerate(('Misfire','Fuel system','Components'))]
    names=('NMHC catalyst','NOx/SCR',None,'Boost pressure',None,'Exhaust gas sensor','Particulate filter','EGR/VVT') if diesel else ('Catalyst','Heated catalyst','Evaporative system','Secondary air','A/C refrigerant','Oxygen sensor','Oxygen heater','EGR/VVT')
    monitors.extend({'name':name,'supported':bool(c&(1<<i)),'complete':not bool(d&(1<<i))} for i,name in enumerate(names) if name)
    return {'MIL':bool(a&128),'stored_dtc_count':a&127,'engine_type':'compression_ignition' if diesel else 'spark_ignition','monitors':monitors,'raw':data.hex().upper()}

def codes(data):
    if len(data)%2:raise ValueError('Odd DTC byte length')
    result=[]
    for a,b in zip(data[::2],data[1::2]):
        if a or b:
            c='PCBU'[a>>6]+str((a>>4)&3)+f'{a&15:X}{b:02X}'
            if c not in result:result.append(c)
    return result

class Cancelled(Exception): pass

class Session:
    def __init__(self,link=LINK):
        self.link=link;self.protocol=None;self.supported={};self.trace=[];self.evidence='physical-unverified';self.identity=''
        self.cancel=None;self.progress=None
    def _check(self):
        if self.cancel is not None and self.cancel.is_set():raise Cancelled()
    def _query(self,command):
        self._check()
        if self.progress:self.progress(command)
        self._check()
        at=stamp()
        try:raw=self.link.query(command)
        except Exception as e:
            self.trace.append({'at':at,'command':command,'error':str(e)});raise
        self.trace.append({'at':at,'command':command,'response':raw})
        return raw
    def _at(self,command):
        if self._query(command).strip().upper()!='OK':raise ValueError('ELM does not support '+command)
    @contextlib.contextmanager
    def _configured(self,cancel=None,progress=None):
        with self.link.lock:
            self.trace=[];self.protocol=None;self.identity='';self.evidence='physical-unverified'
            if self.link.family!='elm':raise ConnectionError('Connect a compatible ELM/STN adapter first; CAN OBD workspace requires ELM')
            self.cancel=cancel;self.progress=progress;self.trace=[]
            configured=False
            try:
                self.identity=self._query('ATI');self.evidence='simulator' if 'GITM_SIMULATOR' in self.identity else 'physical-unverified'
                self._query('0100')
                number=self._query('ATDPN').strip().upper().removeprefix('A')
                if number not in ('6','7','8','9'):raise ValueError('This workspace requires CAN OBD protocol 6–9; legacy read tools remain separate')
                self.protocol=int(number);self.link.protocol=self.protocol;configured=True
                for command in ('ATE0','ATCAF1','ATD0','ATCRA','ATFCSM0','ATSH'+('7DF' if self.protocol in (6,8) else '18DB33F1'),'ATH1'):self._at(command)
                yield
            finally:
                self.cancel=None;self.progress=None
                if configured:
                    try:
                        for command in ('ATH0','ATCRA','ATFCSM0','ATSH'+('7DF' if self.protocol in (6,8) else '18DB33F1')):self._at(command)
                    except Exception:
                        self.link.close();raise ConnectionError('Adapter cleanup failed; disconnected to avoid unknown configuration')
    def _responses(self,command):
        return parse_can(self._query(command),self.protocol)
    def _payloads(self,command,marker):
        result={}
        for ecu,p in self._responses(command).items():
            if p.startswith(b'\x7F'):
                raise ValueError(f'{ecu}: negative response {p.hex().upper()}')
            if not p.startswith(marker):raise ValueError(f'{ecu}: unexpected response to {command}')
            result[ecu]=p[len(marker):]
        return result
    def scan(self,vehicle=None,cancel=None,progress=None):
        report={'format':'gitm-obd-session/1','id':str(uuid.uuid4()),'started_at':stamp(),'vehicle':dict(vehicle or {}),'scope':'Generic emissions CAN OBD responders, not all manufacturer ECUs','status':'complete','ecus':[],'errors':[],'live':[]}
        ecus={};self.supported={}
        def unit(key):
            return ecus.setdefault(key,{'id':key,'supported_pids':[],'vin':None,'dtc':{},'readiness':None,'freeze':None,'errors':[]})
        def error(section,e):
            report['errors'].append({'section':section,'error':str(e)});report['status']='partial'
        try:
            with self._configured(cancel,progress):
                blocks=[0]
                for block in (0,32,64):
                    if block not in blocks:break
                    try:
                        values=self._payloads(f'01{block:02X}',bytes([0x41,block]))
                        for key,data in values.items():
                            if len(data)!=4:raise ValueError('Supported PID bitmap length mismatch')
                            bits=int.from_bytes(data,'big');u=unit(key)
                            u['supported_pids'].extend(block+i for i in range(1,33) if bits&(1<<(32-i)))
                            if bits&1:blocks.append(block+32)
                    except (ValueError,RuntimeError,TimeoutError) as e:error('supported-pids',e)
                self.supported={k:set(u['supported_pids']) for k,u in ecus.items()}
                for mode,label in ((3,'stored'),(7,'pending'),(10,'permanent')):
                    try:
                        values=self._payloads(f'{mode:02X}',bytes([mode+0x40]))
                        for key,u in ecus.items():
                            if key not in values:
                                u['dtc'][label]={'status':'error','codes':[],'error':'ECU did not respond'};error(label,key+' did not respond');continue
                            data=values[key]
                            if not data or len(data)<1+2*data[0] or any(data[1+2*data[0]:]):raise ValueError('DTC count/length mismatch')
                            u['dtc'][label]={'status':'ok','codes':codes(data[1:1+2*data[0]])}
                    except (ValueError,RuntimeError,TimeoutError) as e:
                        error(label,e)
                        for u in ecus.values():u['dtc'].setdefault(label,{'status':'error','codes':[],'error':str(e)})
                for command,marker,section in (('0902',b'\x49\x02','vin'),('0101',b'\x41\x01','readiness')):
                    try:
                        for key,data in self._payloads(command,marker).items():
                            u=unit(key)
                            if section=='vin':
                                if len(data)!=18 or data[0]!=1 or not re.fullmatch(rb'[A-HJ-NPR-Z0-9]{17}',data[1:]):raise ValueError('Invalid VIN response '+key)
                                u['vin']=data[1:].decode('ascii')
                            else:u['readiness']=readiness(data)
                    except (ValueError,RuntimeError,TimeoutError) as e:error(section,e)
                self._freeze(ecus,error)
        except Cancelled:report['status']='cancelled'
        except (ConnectionError,OSError,ValueError,RuntimeError,TimeoutError) as e:error('connection',e)
        report.update(ecus=list(ecus.values()),adapter=self.link.info(),protocol=self.protocol,evidence=self.evidence,adapter_identity=self.identity,trace=list(self.trace),finished_at=stamp())
        if not ecus and report['status']=='complete':report['status']='partial';error('scan','No responding ECUs')
        return report
    def _freeze(self,ecus,error):
        try:maps=self._payloads('020000',b'\x42\x00\x00')
        except (ValueError,RuntimeError,TimeoutError) as e:error('freeze',e);return
        bits={}
        for key,data in maps.items():
            if len(data)!=4:error('freeze','Invalid freeze map '+key);continue
            if key not in ecus:error('freeze','Unexpected ECU '+key);continue
            bits[key]=int.from_bytes(data,'big');ecus[key]['freeze']={'frame':0,'values':[],'trigger_dtc':[]}
        try:
            for key,data in self._payloads('020200',b'\x42\x02\x00').items():
                if key in bits:
                    if len(data)!=2:raise ValueError('Invalid freeze DTC')
                    ecus[key]['freeze']['trigger_dtc']=codes(data)
        except (ValueError,RuntimeError,TimeoutError) as e:error('freeze-dtc',e)
        for pid in PIDS:
            if pid>32 or not any(b&(1<<(32-pid)) for b in bits.values()):continue
            try:
                values=self._payloads(f'02{pid:02X}00',bytes([0x42,pid,0]))
                for key,b in bits.items():
                    if not b&(1<<(32-pid)):continue
                    if key not in values:raise ValueError('Freeze sensor missing '+key)
                    ecus[key]['freeze']['values'].append(decode_pid(pid,values[key]))
            except (ValueError,RuntimeError,TimeoutError) as e:error('freeze-'+f'{pid:02X}',e)
    def live(self,pids,cancel=None):
        if not isinstance(pids,list) or not 1<=len(pids)<=8 or any(type(p)!=int or p not in PIDS for p in pids):raise ValueError('Select 1–8 supported generic PIDs')
        if not self.supported:raise ValueError('Run a scan before live data')
        samples=[]
        try:
            with self._configured(cancel):
                for pid in dict.fromkeys(pids):
                    expected=[key for key,p in self.supported.items() if pid in p]
                    if not expected:continue
                    try:
                        values=self._payloads(f'01{pid:02X}',bytes([0x41,pid]));at=stamp()
                        for ecu in expected:
                            if ecu not in values:samples.append({'ecu':ecu,'pid':pid,'at':at,'error':'ECU did not respond'});continue
                            try:samples.append({'ecu':ecu,'at':at,**decode_pid(pid,values[ecu])})
                            except ValueError as e:samples.append({'ecu':ecu,'pid':pid,'at':at,'error':str(e)})
                    except (ValueError,RuntimeError,TimeoutError) as e:
                        samples.extend({'ecu':key,'pid':pid,'at':stamp(),'error':str(e)} for key in expected)
        except Cancelled:pass
        return samples
    def clear(self,confirm,vehicle=None,cancel=None):
        if confirm is not True:raise ValueError('Explicit clear confirmation required')
        before=self.scan(vehicle,cancel)
        mandatory_errors=any(e['section'] in ('connection','supported-pids','stored') for e in before['errors'])
        if before['status']=='cancelled' or mandatory_errors or not before['ecus'] or any(u['dtc'].get('stored',{}).get('status')!='ok' for u in before['ecus']):raise ValueError('Complete responder discovery and stored-DTC precheck required')
        import store
        store.save(before['vehicle'],'OBD_BEFORE_CLEAR',before)
        keys={u['id'] for u in before['ecus']}
        errors=[];acks=[];clear_trace=[];attempted=False
        try:
            with self._configured(cancel):
                values=self._payloads('010C',b'\x41\x0C')
                if set(values)!=keys or any(len(v)!=2 or int.from_bytes(v,'big') for v in values.values()):raise ValueError('Engine must be stopped; valid zero RPM required from all discovered ECUs')
                self._check()
                store.save(before['vehicle'],'OBD_CLEAR_INTENT',{'before_id':before['id'],'at':stamp(),'scope':'Generic emissions DTC clear; confirmed by user'})
                attempted=True
                replies=self._payloads('04',b'\x44');acks=list(replies)
                if set(acks)!=keys or any(replies.values()):raise ValueError('Clear acknowledgement missing or malformed')
        except (ValueError,RuntimeError,TimeoutError,ConnectionError,OSError,Cancelled) as e:
            if not attempted:raise
            errors.append('Clear may have executed; acknowledgement or cleanup uncertain: '+(str(e) or 'Cancelled'))
        finally:clear_trace=list(self.trace)
        after=self.scan(vehicle,cancel)
        verified=not errors and after['status']!='cancelled' and {u['id'] for u in after['ecus']}==keys and all(u['dtc'].get('stored',{}).get('status')=='ok' and not u['dtc']['stored']['codes'] and u['dtc'].get('pending',{}).get('status')=='ok' and not u['dtc']['pending']['codes'] for u in after['ecus'])
        result={'before':before,'after':after,'acknowledgements':acks,'errors':errors,'trace':clear_trace,'verification_scope':'Stored and pending emissions DTC readback only; permanent DTC not cleared','status':'verified' if verified else 'partial'}
        store.save(before['vehicle'],'OBD_CLEAR_RESULT',result)
        return result
