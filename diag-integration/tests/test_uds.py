import sys
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT.parents[1] / 'source' / 'GearDiag-Raw-Build' / 'app')]
import ecu_scan
import diagnostic_platform


class UDSResponseTests(unittest.TestCase):
    def test_echo_is_ignored(self):
        self.assertEqual(ecu_scan.uds_payload('22F189\r62F1894142', '22F189')['hex'], '4142')

    def test_pending_then_final_in_same_buffer(self):
        result = ecu_scan.uds_payload('7F2278\r62F1894142', '22F189')
        self.assertEqual(result['status'], 'responded')
        self.assertEqual(result['hex'], '4142')

    def test_unresolved_pending_remains_explicit(self):
        self.assertEqual(ecu_scan.uds_payload('7F2278', '22F189')['status'], 'responded_pending')

    def test_vin_requires_exact_valid_17_characters(self):
        for value in ['', 'A', 'I'*17, 'A'*18]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                ecu_scan.uds_payload('62F190'+value.encode().hex(), '22F190')
        vin = '1HGCM82633A004352'
        self.assertEqual(ecu_scan.uds_payload('62F190'+vin.encode().hex(), '22F190')['text'], vin)

    def test_other_dids_require_data(self):
        with self.assertRaises(ValueError):
            ecu_scan.uds_payload('62F189', '22F189')

    def test_malformed_negative_has_no_hidden_bytes(self):
        with self.assertRaises(ValueError):
            ecu_scan.uds_payload('7F223141', '22F189')

    def test_dtc_record_integrity(self):
        self.assertEqual(ecu_scan.uds_payload('5902FF12345608', '1902FF')['dtcs'], [{'uds_code':'123456','status':'08'}])
        for raw in ['59', '5903FF', '5902FF1234']:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                ecu_scan.uds_payload(raw, '1902FF')


class AdapterCleanupTests(unittest.TestCase):
    def run_read(self, reconnect_error=False, identity='4142'):
        class Adapter:
            lock = threading.RLock()
            family, protocol, kind, target, baud = 'elm', 6, 'usb', '/dev/ttyUSB0', 38400
            initialized, disconnected = False, False
            def query(self, request):
                if request == '22F189': return '62F189'+identity
                if request == '22F187': return '62F1874344'
                return 'OK'
            def connect(self, kind, target, baud, family):
                if reconnect_error: raise TimeoutError('restore failed')
                self.initialized = (kind, target, baud, family)
                self.protocol = None
            def close(self):
                self.disconnected = True
                self.family = None
        adapter = Adapter()
        vehicle = {'make':'Test','model':'Car','engine':'E','year':2020}
        model = {'vehicle':vehicle,'source':'documented test source','ecu':'ECU'}
        with patch.object(ecu_scan, 'LINK', adapter), patch.object(diagnostic_platform, 'LINK', adapter), patch.object(diagnostic_platform.store, 'save'):
            try:
                diagnostic_platform.execute_can_read(model, vehicle, '4142', '22F187', {'protocol':'CAN','baudrate':500000,'send_id':'7E0','recv_id':'7E8'}, {})
            except Exception as exc:
                return adapter, exc
        return adapter, None

    def test_success_restores_known_initialized_connection(self):
        adapter, error = self.run_read()
        self.assertIsNone(error)
        self.assertEqual(adapter.initialized, ('usb','/dev/ttyUSB0',38400,'elm'))

    def test_identity_mismatch_still_restores_connection(self):
        adapter, error = self.run_read(identity='FFFF')
        self.assertIsInstance(error, ValueError)
        self.assertTrue(adapter.initialized)

    def test_restore_failure_disconnects(self):
        adapter, error = self.run_read(reconnect_error=True)
        self.assertIsInstance(error, ConnectionError)
        self.assertTrue(adapter.disconnected)


if __name__ == '__main__': unittest.main()
