"""Receive-only SocketCAN and bounded offline frame inspection."""
import csv
import io
import re
import socket
import struct
import threading
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

MAX_ROWS = 10000
MAX_BYTES = 8 * 1024 * 1024
COLUMNS = ['timestamp', 'id', 'flags', 'length', 'data']

def stamp():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds')

def validate_frame(frame):
    if set(frame) != set(COLUMNS): raise ValueError('Unexpected frame fields')
    try:
        when = datetime.fromisoformat(frame['timestamp'])
        if when.utcoffset() != timezone.utc.utcoffset(when): raise ValueError('UTC timestamp required')
        flags = frame['flags'].split('|') if frame['flags'] else []
        if len(flags) != len(set(flags)) or set(flags) - {'EFF','RTR','ERR','FD','BRS','ESI'}: raise ValueError('Invalid flags')
        if ('BRS' in flags or 'ESI' in flags) and 'FD' not in flags: raise ValueError('FD flags require FD')
        if 'RTR' in flags and ('FD' in flags or 'ERR' in flags): raise ValueError('Invalid remote frame')
        if 'ERR' in flags and ('EFF' in flags or 'FD' in flags): raise ValueError('Invalid error frame')
        if not re.fullmatch('[0-9A-F]{3,8}', frame['id']): raise ValueError('Invalid identifier')
        ident = int(frame['id'],16)
        if ident > (0x1fffffff if 'EFF' in flags or 'ERR' in flags else 0x7ff): raise ValueError('Identifier out of range')
        length = frame['length']
        if not isinstance(length,int) or not 0 <= length <= (64 if 'FD' in flags else 8): raise ValueError('Invalid length')
        data = frame['data']
        if not re.fullmatch('[0-9A-F]*', data) or len(data) != (0 if 'RTR' in flags else length*2): raise ValueError('Payload length mismatch')
    except (TypeError, KeyError, OverflowError) as exc: raise ValueError('Invalid frame') from exc
    return frame

def parse_frame(raw, timestamp=None):
    if len(raw) not in (16,72): raise ValueError('Invalid SocketCAN frame size')
    ident,length = struct.unpack_from('=IB',raw)
    flags = [name for mask,name in [(0x80000000,'EFF'),(0x40000000,'RTR'),(0x20000000,'ERR')] if ident & mask]
    if len(raw)==72:
        bits=raw[5]
        if bits & ~7: raise ValueError('Unknown FD flags')
        flags += ['FD'] + [name for mask,name in [(1,'BRS'),(2,'ESI')] if bits & mask]
    return validate_frame({'timestamp':timestamp or stamp(),'id':f'{ident & 0x1fffffff:03X}','flags':'|'.join(flags),'length':length,'data':'' if 'RTR' in flags else raw[8:8+length].hex().upper()})

def parse_csv(raw):
    if not isinstance(raw,bytes) or not 0 < len(raw) <= MAX_BYTES: raise ValueError('CSV must be 1 byte–8 MiB')
    try:
        reader=csv.DictReader(io.StringIO(raw.decode('utf-8-sig')),strict=True)
        if reader.fieldnames != COLUMNS: raise ValueError('Expected CSV header: '+','.join(COLUMNS))
        result=[]
        for row in reader:
            if len(result)>=MAX_ROWS: raise ValueError('CSV exceeds 10,000 frames')
            if None in row or any(v is None or len(v)>128 for v in row.values()): raise ValueError('Invalid CSV row')
            if not re.fullmatch('[0-9]{1,2}',row['length']): raise ValueError('Invalid length')
            row['length']=int(row['length']);result.append(validate_frame(row))
        return result
    except (UnicodeError,csv.Error) as exc: raise ValueError('Invalid UTF-8 frame CSV') from exc

def encode_csv(frames):
    if len(frames)>MAX_ROWS: raise ValueError('Too many frames')
    out=io.StringIO(newline='');writer=csv.DictWriter(out,fieldnames=COLUMNS);writer.writeheader()
    for frame in frames: writer.writerow(validate_frame(frame))
    return out.getvalue().encode('utf-8')

def interfaces():
    result=[]
    for path in Path('/sys/class/net').glob('*'):
        try:
            if path.joinpath('type').read_text().strip()=='280': result.append(path.name)
        except OSError: pass
    return sorted(result)

def capture(name,cancel,receive):
    if not isinstance(name,str) or not re.fullmatch('[A-Za-z0-9_.-]{1,15}',name) or name not in interfaces(): raise ValueError('Select an existing configured CAN interface')
    sock=socket.socket(socket.AF_CAN,socket.SOCK_RAW,socket.CAN_RAW)
    try:
        if hasattr(socket,'CAN_RAW_FD_FRAMES'):
            try:sock.setsockopt(socket.SOL_CAN_RAW,socket.CAN_RAW_FD_FRAMES,1)
            except OSError:pass
        sock.settimeout(.1);sock.bind((name,))
        while not cancel.is_set():
            try: raw=sock.recv(73)
            except socket.timeout:continue
            receive(parse_frame(raw))
    finally:sock.close()

from shiboken6 import isValid
from PySide6.QtCore import QThread, Signal, QTimer
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QTableWidget, QTableWidgetItem, QFileDialog
from professional_components import triple, InfoCard, action_button, configure_table

class Receiver(QThread):
    failure=Signal(str)
    def __init__(self,name,parent):
        super().__init__(parent);self.name=name;self.cancel=threading.Event();self.frames=deque(maxlen=MAX_ROWS);self.lock=threading.Lock();self.count=0
    def receive(self,frame):
        with self.lock:self.frames.append(frame);self.count+=1
    def run(self):
        try:capture(self.name,self.cancel,self.receive)
        except Exception as exc:self.failure.emit(str(exc))
    def stop(self):self.cancel.set()
    def snapshot(self):
        with self.lock:return list(self.frames),self.count

class CANWorkspace(QWidget):
    def __init__(self,window):
        super().__init__(window);self.window=window;self.worker=None;self.recorded=[];self.last_count=-1
        layout=QVBoxLayout(self)
        intro=InfoCard(triple('مساحة CAN للقراءة فقط','Espace CAN en lecture seule','Read-only CAN workspace'))
        note=QLabel(triple('يلزم SocketCAN معدّ مسبقاً. لا إرسال ولا تعديل للمتحكم. الوقت UTC على المضيف عند الاستلام، وليس وقتاً من السلك.','SocketCAN doit être déjà configuré. Aucun envoi ni réglage du contrôleur. Heure UTC du PC à réception, pas du bus.','Requires an already configured SocketCAN interface. No sends or controller configuration. UTC host acquisition time, not wire timestamps.'));note.setWordWrap(True);intro.body.addWidget(note);layout.addWidget(intro)
        controls=QHBoxLayout();self.interface=QComboBox();controls.addWidget(self.interface)
        self.refresh=action_button(triple('تحديث الواجهات','Actualiser les interfaces','Refresh interfaces'));self.start=action_button(triple('بدء الالتقاط','Démarrer la capture','Start capture'),'primary');self.stop_button=action_button(triple('إيقاف','Arrêter','Stop'))
        self.load=action_button(triple('استيراد CSV','Importer CSV','Import CSV'));self.save=action_button(triple('تصدير CSV','Exporter CSV','Export CSV'))
        for button in (self.refresh,self.start,self.stop_button,self.load,self.save):controls.addWidget(button)
        layout.addLayout(controls);self.status=QLabel();self.status.setWordWrap(True);layout.addWidget(self.status)
        self.table=QTableWidget(0,5);self.table.setHorizontalHeaderLabels([triple('وقت UTC','Heure UTC','UTC time'),triple('المعرف','Identifiant','ID'),triple('الأعلام','Indicateurs','Flags'),triple('الطول','Longueur','Length'),triple('البيانات الخام','Données brutes','Raw data')]);configure_table(self.table);layout.addWidget(self.table)
        self.refresh.clicked.connect(self.refresh_interfaces);self.start.clicked.connect(self.begin);self.stop_button.clicked.connect(self.stop_capture);self.load.clicked.connect(self.import_csv);self.save.clicked.connect(self.export_csv)
        self.timer=QTimer(self);self.timer.setInterval(200);self.timer.timeout.connect(self.poll);self.refresh_interfaces();self.update_actions()
    def refresh_interfaces(self):
        self.interface.clear();self.interface.addItems(interfaces());self.status.setText(triple('اختر واجهة معدّة أو استورد CSV. لا بيانات تلقائية.','Choisir une interface configurée ou importer CSV. Aucune donnée automatique.','Select a configured interface or import CSV. No automatic traffic.'));self.update_actions()
    def busy(self):
        task=getattr(self.window,'task',None)
        return getattr(self.window,'_obd_worker',None) is not None or (task is not None and task.isRunning())
    def update_actions(self):
        active=self.worker is not None
        self.start.setEnabled(not active and bool(self.interface.currentText()));self.stop_button.setEnabled(active)
        for control in (self.refresh,self.interface,self.load):control.setEnabled(not active)
        self.save.setEnabled(bool(self.recorded) and not active)
    def begin(self):
        if self.busy():
            self.status.setText(triple('طلب تشخيص جارٍ؛ انتظر','Diagnostic en cours ; attendre','Diagnostic operation busy; wait'));return
        worker=Receiver(self.interface.currentText(),self.window);self.worker=worker;self.window._obd_worker=worker;self.recorded=[];self.last_count=-1
        def finished():
            if isValid(self):self.finished()
            if isValid(self.window) and getattr(self.window,'_obd_worker',None) is worker:self.window._obd_worker=None
            worker.deleteLater()
        worker.failure.connect(self.status.setText);worker.finished.connect(finished);self.window.destroyed.connect(worker.stop);self.timer.start();self.update_actions();worker.start()
        self.status.setText(triple('التقاط استقبال فقط؛ آخر 10000 إطار محفوظة','Réception seule ; 10 000 dernières trames conservées','Receive-only capture; newest 10,000 frames retained'))
    def stop_capture(self):
        if self.worker:self.worker.stop()
    def finished(self):
        self.poll();worker=self.worker;self.timer.stop();self.worker=None
        if getattr(self.window,'_obd_worker',None) is worker:self.window._obd_worker=None
        self.update_actions()
    def poll(self):
        if self.worker:
            frames,count=self.worker.snapshot()
            if count==self.last_count:return
            self.last_count=count;self.recorded=frames;self.render()
    def render(self):
        rows=self.recorded[-600:];self.table.setRowCount(len(rows))
        for i,frame in enumerate(rows):
            for j,key in enumerate(COLUMNS):self.table.setItem(i,j,QTableWidgetItem(str(frame[key])))
        self.update_actions()
    def import_csv(self):
        path,_=QFileDialog.getOpenFileName(self,'CSV','','CSV (*.csv)')
        if not path:return
        try:
            with open(path,'rb') as file:frames=parse_csv(file.read(MAX_BYTES+1))
            self.recorded=frames;self.render();self.status.setText(triple('ملف غير متصل؛ التوقيت كما سجّله المصدر','Fichier hors ligne ; horodatage conservé du fichier','Offline file; timestamps retained from source CSV')+f' · {len(frames)}')
        except (OSError,ValueError) as exc:self.status.setText(str(exc))
    def export_csv(self):
        path,_=QFileDialog.getSaveFileName(self,'CSV','can-frames.csv','CSV (*.csv)')
        if path:
            try:Path(path).write_bytes(encode_csv(self.recorded))
            except (OSError,ValueError) as exc:self.status.setText(str(exc))
    def stop(self):
        self.stop_capture()
    def hideEvent(self,event):
        self.stop_capture();super().hideEvent(event)

def show(window):
    layout=window.page(triple('أدوات CAN','Outils CAN','CAN tools'));workspace=CANWorkspace(window);layout.addWidget(workspace);return workspace
