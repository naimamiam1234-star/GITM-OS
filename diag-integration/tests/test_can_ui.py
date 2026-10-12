import unittest, struct, threading, socket
from unittest.mock import patch
import can_workspace as can

class Frames(unittest.TestCase):
    def test_classic_extended_remote_error_fd(self):
        for ident,flags in [(0x123,''),(0x80012345,'EFF'),(0x40000123,'RTR'),(0x20000004,'ERR')]:
            f=can.parse_frame(struct.pack('=IB3x8s',ident,2,b'\x01\x02'), '2026-10-12T01:02:03+00:00')
            self.assertEqual(f['flags'],flags); self.assertEqual(f['length'],2)
            self.assertEqual(f['data'],'' if flags=='RTR' else '0102')
        f=can.parse_frame(struct.pack('=IBB2x64s',0x123,12,1,bytes(range(12))))
        self.assertEqual(f['flags'],'FD|BRS');self.assertEqual(f['length'],12)
    def test_malformed(self):
        for raw in [b'',b' '*17,struct.pack('=IB3x8s',1,9,b''),struct.pack('=IBB2x64s',1,65,0,b''),struct.pack('=IB3x8s',0x1000,1,b''),struct.pack('=IBB2x64s',0x40000123,1,0,b'')]:
            with self.assertRaises(ValueError):can.parse_frame(raw)
    def test_csv_roundtrip_and_bounds(self):
        frame=can.parse_frame(struct.pack('=IB3x8s',0x123,2,b'\x01\x02'))
        self.assertEqual(can.parse_csv(can.encode_csv([frame])),[frame])
        for raw in [b'',b'timestamp,id,flags,length,data\n2026-01-01T00:00:00+00:00,123,,-1,\n',b'x'*(8*1024*1024+1),b'timestamp,id,flags,length,data\n2026-01-01T00:00:00+00:00,123,,2,01\n']:
            with self.assertRaises(ValueError):can.parse_csv(raw)
    def test_read_only_capture_and_close(self):
        cancel=threading.Event()
        class Fake:
            def __init__(self,*args):self.closed=False;self.bound=None
            def setsockopt(self,*args):pass
            def bind(self,address):self.bound=address
            def settimeout(self,value):pass
            def recv(self,n):cancel.set();return struct.pack('=IB3x8s',0x123,1,b'\x01')
            def close(self):self.closed=True
            def send(self,*args):raise AssertionError('Must never send')
        s=Fake(); frames=[]
        with patch.object(can,'interfaces',return_value=['vcan0']),patch.object(can.socket,'socket',return_value=s):can.capture('vcan0',cancel,frames.append)
        self.assertEqual(s.bound,('vcan0',));self.assertTrue(s.closed);self.assertEqual(frames[0]['data'],'01')
        with self.assertRaises(ValueError):can.capture('../bad',cancel,frames.append)


class WorkspaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app=QApplication.instance() or QApplication([])
    def test_busy_does_not_open_socket(self):
        from PySide6.QtWidgets import QWidget
        window=QWidget();window._obd_worker=object();window.task=None
        with patch.object(can,'interfaces',return_value=['vcan0']):page=can.CANWorkspace(window)
        with patch.object(can.socket,'socket') as connect:page.begin()
        connect.assert_not_called();self.assertIsNone(page.worker)
        page.deleteLater();window.deleteLater();self.app.processEvents()
    def test_table_retention_does_not_change_export(self):
        from PySide6.QtWidgets import QWidget
        window=QWidget();window._obd_worker=None;window.task=None
        with patch.object(can,'interfaces',return_value=[]):page=can.CANWorkspace(window)
        frame=can.parse_frame(struct.pack('=IB3x8s',0x123,1,b'\x01'))
        page.recorded=[frame]*650;page.render()
        self.assertEqual(page.table.rowCount(),600);self.assertEqual(len(can.parse_csv(can.encode_csv(page.recorded))),650)
        self.assertFalse(page.start.isEnabled());self.assertTrue(page.save.isEnabled())
        page.deleteLater();window.deleteLater();self.app.processEvents()
    def test_pending_receive_buffer_is_bounded(self):
        worker=can.Receiver('vcan0',None)
        frame=can.parse_frame(struct.pack('=IB3x8s',0x123,1,b'\x01'))
        for _ in range(10005):worker.receive(frame)
        rows,total=worker.snapshot();self.assertEqual(len(rows),10000);self.assertEqual(total,10005)
    def test_deleted_page_releases_worker_after_cancel(self):
        import time
        from PySide6.QtWidgets import QWidget
        from PySide6.QtCore import QCoreApplication, QEvent
        window=QWidget();window._obd_worker=None;window.task=None
        class Idle:
            def setsockopt(self,*args):pass
            def settimeout(self,value):pass
            def bind(self,address):pass
            def recv(self,n):time.sleep(.01);raise socket.timeout()
            def close(self):self.closed=True
        sock=Idle();sock.closed=False
        with patch.object(can,'interfaces',return_value=['vcan0']),patch.object(can.socket,'socket',return_value=sock):
            page=can.CANWorkspace(window);page.begin();worker=page.worker
            page.stop();page.deleteLater();QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)
            deadline=time.monotonic()+1
            while window._obd_worker is not None and time.monotonic()<deadline:self.app.processEvents();time.sleep(.01)
            self.assertIsNone(window._obd_worker);self.assertTrue(sock.closed)
        window.deleteLater();self.app.processEvents()

if __name__=='__main__':unittest.main()
