import json
import pathlib
import sys
import threading
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT.parents[1] / 'source/GearDiag-Raw-Build/app')]
import ecu_workspace as workspace


def profile():
    return {'format':'gitm-ecu-profile/1','validated':True,'source':'TEST FIXTURE ONLY, not an OEM vehicle definition','vehicle':{'make':'Fixture','model':'Car','years':[2020],'engine':'TEST'},'bus':{'type':'hs-can','protocol':6},'ecus':[{'name':'Test ECU','tx_id':'7E0','rx_id':'7E8','reads':['vin','dtc'],'live_data':[{'name':'Test voltage','did':'1234','length':2,'scale':0.001,'unit':'V'}]}]}


class ProfileBoundaryTests(unittest.TestCase):
    def test_import_validates_without_adapter_traffic(self):
        with patch.object(workspace.LINK, 'query') as query, patch.object(workspace.LINK, 'connect') as connect:
            self.assertEqual(workspace.parse_profile(json.dumps(profile()).encode())['vehicle']['make'], 'Fixture')
        query.assert_not_called()
        connect.assert_not_called()

    def test_malformed_or_oversized_import_rejected(self):
        for raw in [b'[]', b'{', b' '*262145, b'{}']:
            with self.subTest(raw=raw[:12]), self.assertRaises(ValueError): workspace.parse_profile(raw)

    def test_write_operation_denied_on_import(self):
        p = profile();p['ecus'][0]['reads']=['write']
        with self.assertRaises(ValueError):workspace.parse_profile(json.dumps(p).encode())

    def test_vehicle_year_and_engine_must_match(self):
        vehicle={'make':'Fixture','model':'Car','year':2020,'engine':'TEST'}
        self.assertEqual(workspace.match_vehicle(profile(),vehicle),vehicle)
        for key,value in [('year',2021),('year','invalid'),('engine','OTHER'),('make','Other')]:
            with self.subTest(key=key), self.assertRaises(ValueError):workspace.match_vehicle(profile(),{**vehicle,key:value})

    def test_protocol_established_explicitly_before_scan(self):
        vehicle={'make':'Fixture','model':'Car','year':2020,'engine':'TEST'}
        with patch.object(workspace.LINK,'family','elm'),patch.object(workspace.LINK,'protocol',None),patch.object(workspace.LINK,'query',side_effect=['410000000000','A6']) as query,patch.object(workspace.ecu_scan,'scan_profile',return_value={'units':[]}) as scan:
            self.assertEqual(workspace.run_scan(profile(),vehicle,0,False,threading.Event()),{'units':[]})
            self.assertEqual([c.args[0] for c in query.call_args_list],['0100','ATDPN'])
            scan.assert_called_once_with(profile(),vehicle,0,False)

    def test_wrong_protocol_or_invalid_vehicle_never_scans(self):
        vehicle={'make':'Fixture','model':'Car','year':2020,'engine':'TEST'}
        with patch.object(workspace.LINK,'family','elm'),patch.object(workspace.LINK,'protocol',8),patch.object(workspace.ecu_scan,'scan_profile') as scan:
            with self.assertRaises(ValueError):workspace.run_scan(profile(),vehicle,0,False,threading.Event())
            with self.assertRaises(ValueError):workspace.run_scan(profile(),{**vehicle,'year':2021},0,False,threading.Event())
            scan.assert_not_called()

    def test_cancel_before_start_sends_nothing(self):
        cancel=threading.Event();cancel.set()
        with patch.object(workspace.LINK,'query') as query,patch.object(workspace.ecu_scan,'scan_profile') as scan:
            with self.assertRaises(RuntimeError):workspace.run_scan(profile(),{'make':'Fixture','model':'Car','year':2020,'engine':'TEST'},0,False,cancel)
            query.assert_not_called();scan.assert_not_called()


class NativeProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from PySide6.QtWidgets import QApplication
        except ImportError:
            raise unittest.SkipTest('Qt runtime is required for native UI checks')
        cls.app = QApplication.instance() or QApplication([])

    def create_workspace(self):
        from PySide6.QtWidgets import QMainWindow
        window=QMainWindow();window.vehicle={};window.task=None
        page=workspace.workspace_class()(window);window.setCentralWidget(page)
        self.addCleanup(window.close)
        return window,page

    def test_profile_ui_import_never_executes_vehicle_requests(self):
        window,page=self.create_workspace()
        with patch.object(workspace.LINK,'query') as query,patch.object(workspace.LINK,'connect') as connect,patch.object(workspace.ecu_scan,'scan_profile') as scan:
            page.load_profile(json.dumps(profile()).encode())
            self.assertEqual(page.selection.count(),2)
            self.assertEqual(page.fields['year'].text(),'2020')
            self.assertIn('TEST FIXTURE ONLY',page.source.text())
            self.assertIsNone(page.worker)
            self.assertEqual(window.vehicle,{})
            query.assert_not_called();connect.assert_not_called();scan.assert_not_called()

    def test_invalid_year_ui_blocks_before_worker(self):
        window,page=self.create_workspace();page.load_profile(json.dumps(profile()).encode())
        page.fields['year'].setText('2021')
        with patch.object(page,'launch') as launch:
            page.acquire(False);launch.assert_not_called()
        self.assertIsNone(page.worker)

    def test_existing_obd_worker_blocks_acquisition(self):
        window,page=self.create_workspace();window._obd_worker=object()
        with patch('diagnostic_workspace.Worker') as worker:
            page.launch(lambda *_:None,lambda _:None);worker.assert_not_called()
        self.assertIsNone(page.worker)


if __name__ == '__main__':unittest.main()
