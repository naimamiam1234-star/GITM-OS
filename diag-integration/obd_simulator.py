"""Loopback-only ELM/ECU bench fixture. Identity explicitly says SIMULATOR."""
import socketserver, threading, argparse, time

def bitmap(pids,block):
    bits=sum(1<<(32-(p-block)) for p in pids if block<p<=block+32)
    return bits.to_bytes(4,'big')

class Simulator:
    def __init__(self,port=0):
        self.headers=False;self.commands=[];self.protocol=6;self.rpm=1726;self.cleared=False;self.pending_error=False;self.missing_ack=False;self.drop_live=False;self.permanent_unsupported=False
        self.pids={1,2,4,5,6,7,11,12,13,15,16,17,31,32,33,47,49,51,64,66,67,68,70,73,74,92,94}
        self.rx_filter=None
        fixture=self
        class Handler(socketserver.BaseRequestHandler):
            def handle(self):
                buffer=b''
                while True:
                    try:data=self.request.recv(4096)
                    except OSError:return
                    if not data:return
                    buffer+=data
                    while b'\r' in buffer:
                        command,buffer=buffer.split(b'\r',1)
                        raw=fixture.reply(command.decode().strip().upper().replace(' ',''))
                        self.request.sendall((raw+'\r>').encode())
        class Server(socketserver.ThreadingTCPServer):
            allow_reuse_address=True;daemon_threads=True
        self.server=Server(('127.0.0.1',port),Handler);self.port=self.server.server_address[1];self.thread=None
    def start(self):
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();return self
    def stop(self):
        self.server.shutdown();self.server.server_close()
        if self.thread:self.thread.join(2)
    def frames(self,ecu,data):
        header=ecu if self.protocol in (6,8) else ('18DAF110' if ecu=='7E8' else '18DAF118')
        if not self.headers:
            if len(data)<=7:return data.hex().upper()
            chunks=[data[:6]]+[data[i:i+7] for i in range(6,len(data),7)]
            return f'{len(data):03X}\r'+'\r'.join(f'{i}: '+chunk.hex(' ').upper() for i,chunk in enumerate(chunks))
        if len(data)<=7:return header+' '+(bytes([len(data)])+data).hex(' ').upper()
        lines=[header+' '+(bytes([0x10|(len(data)>>8),len(data)&255])+data[:6]).hex(' ').upper()]
        rest=data[6:];seq=1
        while rest:
            chunk=rest[:7];rest=rest[7:];lines.append(header+' '+(bytes([0x20|seq])+chunk).hex(' ').upper());seq=(seq+1)&15
        return '\r'.join(lines)
    def sensor(self,pid,ecu):
        values={4:b'\x40',5:b'\x7D',6:b'\x80',7:b'\x84',11:b'\x28',12:int((self.rpm+(100 if ecu=='7E9' and self.rpm else 0))*4).to_bytes(2,'big'),13:b'\x00',15:b'\x50',16:b'\x02\x58',17:b'\x20',31:b'\x00\x78',33:b'\x00\x00',47:b'\x80',49:b'\x03\xE8',51:b'\x65',66:b'\x36\xB0',67:b'\x01\x00',68:b'\x80\x00',70:b'\x50',73:b'\x10',74:b'\x10',92:b'\x82',94:b'\x00\x28'}
        return values.get(pid)
    def reply(self,command):
        self.commands.append(command)
        if command=='ATI':return 'ELM327 v2.3 GITM_SIMULATOR'
        if command=='ATDPN':return 'A'+str(self.protocol)
        if command=='ATDP':return 'ISO 15765-4 CAN (SIMULATED)'
        if command=='0A' and self.permanent_unsupported:return 'NO DATA'
        if command=='ATRV':return '13.8V'
        if command.startswith('AT'):
            if command=='ATH1':self.headers=True
            if command in ('ATH0','ATD'):self.headers=False
            if command=='ATD':self.rx_filter=None
            if command.startswith('ATCRA'):self.rx_filter=command[5:] or None
            return 'OK'
        if command=='04':self.cleared=True;return '\r'.join(self.frames(e,b'\x44') for e in (('7E8',) if self.missing_ack else ('7E8','7E9')))
        output=[]
        for ecu in ('7E9','7E8') if len(self.commands)%2 else ('7E8','7E9'):
            if self.rx_filter and self.rx_filter!=ecu:continue
            data=None
            if command in ('0100','0120','0140'):
                data=b'\x41'+bytes([int(command[2:],16)])+bitmap(self.pids,int(command[2:],16))
            elif command=='0902':data=b'\x49\x02\x01VF1AAAAAAA1234567'
            elif command=='22F190':data=b'\x62\xF1\x90VF1AAAAAAA1234567'
            elif command=='22F189':data=b'\x62\xF1\x89SWM2'
            elif command=='22F187':data=b'\x62\xF1\x87SIM-PART'
            elif command=='22F18C':data=b'\x62\xF1\x8CBENCH123'
            elif command=='22F40C':data=b'\x62\xF4\x0C'+self.sensor(12,ecu)
            elif command=='1902FF':data=bytes.fromhex('5902FF01020308')
            elif command=='0101':data=b'\x41\x01'+(bytes.fromhex('84016501') if ecu=='7E8' and not self.cleared else bytes.fromhex('00076500'))
            elif command in ('03','07','0A'):
                mode=int(command,16)
                if mode==7 and self.pending_error:data=b'\x7F\x07\x11'
                elif ecu=='7E9':data=bytes([mode+64,0])
                elif mode==3:data=bytes.fromhex('43040100020003000400') if not self.cleared else b'\x43\x00'
                elif mode==7:data=bytes.fromhex('47010133') if not self.cleared else b'\x47\x00'
                else:data=bytes.fromhex('4A010420')
            elif command.startswith('01') and len(command)==4:
                pid=int(command[2:],16);value=self.sensor(pid,ecu)
                if value is not None and not (self.drop_live and ecu=='7E9'):data=bytes([0x41,pid])+value
            elif command=='020000' and ecu=='7E8':data=b'\x42\x00\x00'+bitmap({5,12,13},0)
            elif command=='020200' and ecu=='7E8':data=bytes.fromhex('4202000100')
            elif command.startswith('02') and len(command)==6 and ecu=='7E8':
                pid=int(command[2:4],16)
                if pid in (5,12,13):data=bytes([0x42,pid,0])+self.sensor(pid,ecu)
            if data is not None:output.append(self.frames(ecu,data))
        return '\r'.join(output) if output else 'NO DATA'

if __name__=='__main__':
    parser=argparse.ArgumentParser(description='SIMULATOR ONLY — no physical vehicle connection')
    parser.add_argument('--port',type=int,default=35000);args=parser.parse_args()
    server=Simulator(args.port).start();print(f'GITM SIMULATOR — 127.0.0.1:{server.port}',flush=True)
    try:
        while True:time.sleep(1)
    except KeyboardInterrupt:server.stop()
