import sys, pathlib, unittest, threading
from unittest.mock import patch
sys.path[:0]=[str(pathlib.Path(__file__).resolve().parents[1]),str(pathlib.Path(__file__).resolve().parents[3]/'source/GearDiag-Raw-Build/app')]
from obd_session import parse_can, decode_pid, readiness, Session
from obd_simulator import Simulator
from transport import Link

class Frames(unittest.TestCase):
 def test_interleaved_multiframe(self):
  raw='7E8 10 0A 43 04 01 00 02 00\r7E9 03 43 00 00\r7E8 21 03 00 04 00 00 00 00'
  self.assertEqual(parse_can(raw,6),{'7E8':bytes.fromhex('43040100020003000400'),'7E9':bytes.fromhex('430000')})
 def test_sequence_and_truncation_rejected(self):
  for raw in ['7E8 10 0A 43 04 01 00 02 00','7E8 10 0A 43 04 01 00 02 00\r7E8 22 03 00 04 00 00 00 00','7E8 06 41 00 00']:
   with self.assertRaises(ValueError):parse_can(raw,6)
 def test_29bit_and_no_marker_search(self):
  self.assertEqual(parse_can('18DAF110 04 41 0C 1A F8',7),{'18DAF110':bytes.fromhex('410C1AF8')})
  with self.assertRaises(ValueError):parse_can('410C1AF8',6)
 def test_pid_formula_and_length(self):
  self.assertEqual(decode_pid(0x0C,bytes.fromhex('1AF8'))['value'],1726)
  self.assertEqual(decode_pid(0x06,b'\x80')['value'],0)
  self.assertAlmostEqual(decode_pid(0x42,bytes.fromhex('36B0'))['value'],14)
  with self.assertRaises(ValueError):decode_pid(0x0C,b'\x1A')
 def test_readiness_bit_layout(self):
  r=readiness(bytes.fromhex('81016501'))
  self.assertTrue(r['MIL']);self.assertEqual(r['stored_dtc_count'],1)
  self.assertEqual(r['engine_type'],'spark_ignition')
  catalyst=next(m for m in r['monitors'] if m['name']=='Catalyst')
  self.assertTrue(catalyst['supported']);self.assertFalse(catalyst['complete'])
  r=readiness(bytes.fromhex('00082C20'))
  self.assertEqual(r['engine_type'],'compression_ignition')
  self.assertFalse(next(m for m in r['monitors'] if m['name']=='Exhaust gas sensor')['complete'])

class TCP(unittest.TestCase):
 def setUp(self):
  self.server=Simulator();self.server.start();self.link=Link();self.link.connect('wifi',f'127.0.0.1:{self.server.port}',family='elm');self.session=Session(self.link)
 def tearDown(self):self.link.close();self.server.stop()
 def test_real_transport_scan_and_live_per_ecu(self):
  r=self.session.scan({'make':'Test','model':'Bench'})
  self.assertEqual(r['status'],'complete');self.assertEqual(r['evidence'],'simulator')
  e={x['id']:x for x in r['ecus']}
  self.assertEqual(e['7E8']['vin'],'VF1AAAAAAA1234567')
  self.assertEqual(e['7E8']['dtc']['stored']['codes'],['P0100','P0200','P0300','P0400'])
  self.assertEqual(e['7E9']['dtc']['stored']['codes'],[])
  self.assertEqual(e['7E8']['dtc']['pending']['codes'],['P0133'])
  self.assertEqual(e['7E8']['freeze']['trigger_dtc'],['P0100'])
  data=self.session.live([0x0C,0x0D]);rpm={d['ecu']:d['value'] for d in data if d['pid']==0x0C}
  self.assertNotEqual(rpm['7E8'],rpm['7E9']);self.assertFalse(self.server.headers)
 def test_clear_refuses_running_engine_and_no_confirmation(self):
  self.session.scan()
  with self.assertRaises(ValueError):self.session.clear(False)
  with self.assertRaises(ValueError):self.session.clear(True)
  self.assertNotIn('04',self.server.commands)
 def test_clear_verified_only_after_saved_precheck(self):
  self.server.rpm=0;self.session.scan();r=self.session.clear(True)
  self.assertEqual(r['status'],'verified');self.assertTrue(r['before']['ecus'][0]['dtc']['stored']['codes'])
  self.assertFalse(r['after']['ecus'][0]['dtc']['stored']['codes'])
  self.assertTrue(next(e for e in r['after']['ecus'] if e['id']=='7E8')['dtc']['permanent']['codes'])
 def test_29bit_tcp(self):
  self.server.protocol=7;r=self.session.scan()
  self.assertEqual(r['status'],'complete');self.assertEqual({e['id'] for e in r['ecus']},{'18DAF110','18DAF118'})
 def test_missing_clear_ack_returns_uncertain_postcheck(self):
  self.server.rpm=0;self.server.missing_ack=True;r=self.session.clear(True)
  self.assertEqual(r['status'],'partial');self.assertIn('04',self.server.commands)
  self.assertTrue(r['errors']);self.assertTrue(r['after']['ecus'])
 def test_cable_loss_after_clear_is_saved_as_uncertain(self):
  import store
  self.server.rpm=0;query=self.link.query
  def pull(command):
   result=query(command)
   if command=='04':self.link.close();raise ConnectionError('Simulated cable loss after clear')
   return result
  with patch.object(self.link,'query',side_effect=pull),patch.object(store,'save') as save:
   result=self.session.clear(True)
   self.assertEqual(result['status'],'partial');self.assertTrue(result['errors'])
   self.assertIn('may have executed',' '.join(result['errors']))
   self.assertTrue(any(t['command']=='04' for t in result['trace']))
   self.assertTrue(any(call.args[1]=='OBD_CLEAR_RESULT' for call in save.call_args_list))
 def test_live_requires_scan_and_recovers_missing_ecu(self):
  with self.assertRaises(ValueError):self.session.live([12])
  self.session.scan();self.server.drop_live=True
  samples=self.session.live([12]);self.assertTrue(any(s.get('error') and s['ecu']=='7E9' for s in samples))
 def test_optional_permanent_unsupported_does_not_block_confirmed_clear(self):
  self.server.rpm=0;self.server.permanent_unsupported=True
  result=self.session.clear(True)
  self.assertEqual(result['status'],'verified');self.assertEqual(result['before']['status'],'partial')
  self.assertEqual(result['after']['ecus'][0]['dtc']['permanent']['status'],'error')
 def test_disconnected_scan_never_reuses_old_evidence(self):
  self.session.scan();self.link.close();result=self.session.scan()
  self.assertEqual(result['trace'],[]);self.assertEqual(result['ecus'],[]);self.assertIsNone(result['protocol'])
 def test_real_documented_profile_and_reinitialized_second_read(self):
  import ecu_scan,ecu_workspace,diagnostic_platform
  v={'make':'Test','model':'Bench','year':2020,'engine':'SIM'}
  profile={'format':'gitm-ecu-profile/1','validated':True,'source':'GITM_SIMULATOR test fixture only','vehicle':{'make':'Test','model':'Bench','years':[2020],'engine':'SIM'},'bus':{'type':'hs-can','protocol':6},'ecus':[{'name':'Simulated engine','tx_id':'7E0','rx_id':'7E8','reads':['vin','dtc'],'live_data':[{'name':'Bench RPM','did':'F40C','length':2,'scale':.25,'unit':'rpm'}]}]}
  with patch.object(ecu_scan,'LINK',self.link),patch.object(ecu_workspace,'LINK',self.link),patch.object(diagnostic_platform,'LINK',self.link):
   r=ecu_workspace.run_scan(profile,v,0,False,threading.Event())
   self.assertEqual(r['units'][0]['reads']['vin']['text'],'VF1AAAAAAA1234567')
   r=ecu_workspace.run_scan(profile,v,0,True,threading.Event())
   self.assertEqual(r['units'][0]['reads']['Bench RPM']['value'],1726)
   for _ in range(2):
    self.link.protocol=6
    r=diagnostic_platform.execute_can_read({'vehicle':v,'source':profile['source'],'ecu':'Simulator'},v,b'SWM2'.hex(),'22F187',{'protocol':'CAN','baudrate':500000,'send_id':'7E0','recv_id':'7E8'},{'fixture':True})
    self.assertTrue(r['sent_to_vehicle']);self.assertEqual(r['result']['text'],'SIM-PART')
 def test_cancellation_and_negative_not_clean(self):
  cancel=threading.Event()
  def progress(s):
   if s=='03':cancel.set()
  r=self.session.scan(cancel=cancel,progress=progress)
  self.assertEqual(r['status'],'cancelled');self.assertFalse(self.server.headers)
  self.server.pending_error=True;r=self.session.scan();self.assertEqual(r['status'],'partial')
  self.assertEqual(r['ecus'][0]['dtc']['pending']['status'],'error')

if __name__=='__main__':unittest.main()
