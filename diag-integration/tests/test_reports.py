import unittest, sys, tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from diagnostic_reports import html_report, export_csv, write_report
class Reports(unittest.TestCase):
 def test_escape_and_errors(self):
  text=html_report({'status':'partial','vehicle':{'model':'<script>'},'ecus':[], 'errors':[{'section':'VIN','error':'No data'}]})
  self.assertNotIn('<script>',text);self.assertIn('&lt;script&gt;',text);self.assertIn('No data',text)
 def test_structured_tables_and_simulator(self):
  text=html_report({'evidence':'simulator','ecus':[{'id':'7E8','dtc':{'stored':{'status':'ok','codes':['P0300']}},'readiness':{'monitors':[{'name':'Catalyst','supported':True,'complete':False}]},'freeze':{'frame':0,'values':[{'pid':12,'name':'RPM','value':850,'unit':'rpm'}]}}]})
  self.assertIn('<table>',text);self.assertIn('SIMULATOR',text);self.assertIn('P0300',text);self.assertIn('Catalyst',text);self.assertIn('850',text);self.assertNotIn('<pre>',text)
 def test_html_includes_live_samples(self):
  text=html_report({'live':[{'session_id':'session-A','evidence':'simulator','ecu':'7E8','pid':12,'name':'unique_parameter','value':9876,'unit':'rpm'}]})
  self.assertIn('unique_parameter',text);self.assertIn('9876',text);self.assertIn('session-A',text)
 def test_unsupported_monitor_has_no_completion_claim(self):
  text=html_report({'ecus':[{'id':'7E8','readiness':{'monitors':[{'name':'Unsupported fixture','supported':False,'complete':None}]}}]})
  self.assertIn('Not supported',text)
  self.assertIn('Unsupported fixture',text)
 def test_csv(self):
  text=export_csv([{'ecu':'7E8','pid':12,'name':'RPM','value':900,'unit':'rpm','at':'now'},{'ecu':'7E8','pid':13,'error':'No data'}])
  self.assertIn('900',text);self.assertIn('No data',text)
 def test_write(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'r.json';write_report(p,{'status':'cancelled'});self.assertIn('cancelled',p.read_text())
if __name__=='__main__':unittest.main()
