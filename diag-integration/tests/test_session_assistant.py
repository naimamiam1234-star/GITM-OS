import unittest, tempfile, json, threading
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

class ContextTests(unittest.TestCase):
 def core(self):
  try: import assistant_core; return assistant_core
  except ImportError: self.fail('Session assistant core missing')
 def test_observed_vehicle_and_ecu_scope_privacy(self):
  c=self.core(); report={'id':'scan-1','evidence':'simulator','vehicle':{'make':'Renault','model':'Clio','vin':'VF1AAAAAA12345678','phone':'secret'},'ecus':{'7E8':{'dtc':{'stored':{'codes':['P0300']}}}}}
  samples=[{'ecu':'7E8','pid':12,'value':900,'unit':'rpm'},{'ecu':'7E9','pid':12,'value':3000}]
  snap=c.snapshot(report,{'make':'BMW'},'7E8','P0300',samples,[12],'VIN VF1AAAAAA12345678')
  self.assertEqual(snap['vehicle']['make'],'Renault'); self.assertEqual(snap['mode'],'simulator');self.assertEqual(len(snap['samples']),1)
  self.assertNotIn('VF1AAAAAA12345678',json.dumps(snap));report['vehicle']['model']='Other';self.assertEqual(snap['vehicle']['model'],'Clio')
 def test_offline_identity_stable_and_report_identity_distinct(self):
  c=self.core();a=c.snapshot(None,{'make':'A','vin':'ABC'});b=c.snapshot(None,{'make':'A','vin':'XYZ'});self.assertNotEqual(a['session_id'],b['session_id']);self.assertEqual(a['mode'],'offline')
  self.assertEqual(a['session_id'],c.snapshot(None,{'make':'A','vin':'ABC'})['session_id'])
 def test_history_isolated_and_url_validation(self):
  c=self.core()
  with tempfile.TemporaryDirectory() as d:
   db=Path(d)/'history.db';c.record('one','analysis',{'text':'measured'},db);c.record('two','note',{'text':'other'},db)
   self.assertEqual(len(c.history('one',db)),1)
  for url in ['javascript:alert(1)','file:///tmp/a','https://user:pass@example.com','http://127.0.0.1/a','https://example.com/?key=secret','https://localhost/a']:
   with self.assertRaises(ValueError):c.safe_url(url)
  self.assertEqual(c.safe_url('https://www.youtube.com/watch?v=abcdefghijk'),'https://www.youtube.com/watch?v=abcdefghijk')
  with self.assertRaises(ValueError):c.safe_url('https://[fd00::1]/a')
 def test_selected_ecu_report_only_and_bounded_samples(self):
  c=self.core();r={'id':'a','vehicle':{'make':'A'},'ecus':[{'id':'7E8','dtc':{'codes':['P0300']}},{'id':'7E9','dtc':{'codes':['P0200']}}]}
  snap=c.snapshot(r,ecu='7E8',samples=[{'ecu':'7E8','pid':12,'value':n} for n in range(90)])
  self.assertEqual([r['id'] for r in snap['report']['ecus']],['7E8']);self.assertEqual(len(snap['samples']),30)
 def test_retrieval_requires_consent_and_no_key_does_not_fabricate(self):
  c=self.core()
  with patch.object(c,'request_json') as call:
   with self.assertRaises(ValueError):c.search_external('P0300','brave','key',False,threading.Event())
   with self.assertRaises(ValueError):c.search_external('P0300','brave','',True,threading.Event())
   call.assert_not_called()
 def test_real_api_mapping_filters_urls_and_labels_snippet(self):
  c=self.core()
  with patch.object(c,'request_json',return_value={'web':{'results':[{'title':'Example','url':'https://example.com/a','description':'Measured excerpt'},{'title':'bad','url':'javascript:alert(1)'}]}}) as call:
   rows=c.search_external('P0300','brave','key',True,threading.Event());self.assertEqual(len(rows),1);self.assertEqual(rows[0]['content_type'],'search_snippet');self.assertEqual(rows[0]['text'],'Measured excerpt')
   self.assertEqual(call.call_args.args[0].headers['X-subscription-token'],'key')
  with patch.object(c,'request_json',return_value={'items':[{'id':{'videoId':'abcdefghijk'},'snippet':{'title':'Video','description':'Description'}}]}):
   row=c.search_external('P0300','youtube','key',True,threading.Event())[0];self.assertEqual(row['content_type'],'video_description');self.assertFalse(row['transcript_read'])

class PanelTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  from PySide6.QtWidgets import QApplication
  cls.app=QApplication.instance() or QApplication([])
 def window(self):
  import native,professional_ui
  w=native.Window();professional_ui.install(w);self.addCleanup(w.close);return w,w.professional_shell
 def test_top_button_keeps_page_and_reuses_panel(self):
  w,s=self.window();s.navigate('diagnosis');page=w.pages.currentWidget();workspace=w.diagnostic_workspace;tab=workspace.tabs.currentIndex()
  self.assertTrue(hasattr(s,'assistant_button'),'Persistent assistant button missing')
  s.assistant_button.click();self.app.processEvents();panel=s.assistant_panel
  self.assertIs(w.pages.currentWidget(),page);self.assertEqual(workspace.tabs.currentIndex(),tab)
  s.assistant_button.click();s.assistant_button.click();self.assertIs(s.assistant_panel,panel);self.assertIs(w.pages.currentWidget(),page)
 def test_context_open_does_not_talk_to_adapter_or_stop_live(self):
  w,s=self.window();s.navigate('diagnosis');ws=w.diagnostic_workspace;ws.live_on=True
  with patch.object(ws,'stop') as stop,patch('transport.LINK.query') as query:
   s.show_assistant();s.assistant_panel.analyze();query.assert_not_called();stop.assert_not_called()
 def test_browser_open_is_recorded_without_changing_page(self):
  w,s=self.window();s.navigate('diagnosis');page=w.pages.currentWidget();s.show_assistant();panel=s.assistant_panel
  from PySide6.QtCore import QUrl
  with patch('session_assistant.QDesktopServices.openUrl',return_value=True) as browser:
   panel.open_source(QUrl('https://example.com/repair'));browser.assert_called_once()
  self.assertIs(w.pages.currentWidget(),page);self.assertIn('opened_source',[r['kind'] for r in panel.events()])
 def test_detach_clears_all_cloud_evidence(self):
  w,s=self.window();s.show_assistant();cloud=s.assistant_panel.cloud;self.assertTrue(cloud.evidence_override);cloud.detach();self.assertIsNone(cloud.attachment);self.assertIsNone(cloud.evidence_override)
 def test_restore_sources_and_note_for_same_session(self):
  w,s=self.window();w.vehicle={'make':'A','model':'Journal test'};s.show_assistant();panel=s.assistant_panel
  import assistant_core as c
  c.record(panel.context['session_id'],'search_results',{'query':'a','provider':'brave','context_fingerprint':panel.context['fingerprint'],'results':[{'title':'Known result','text':'Snippet','url':'https://example.com/a','provider':'brave','content_type':'search_snippet'}]})
  panel.capture();self.assertIn('Known result',panel.results.toPlainText())
  panel.symptoms.setPlainText('A different symptom');panel.capture();self.assertNotIn('Known result',panel.results.toPlainText())
 def test_contextual_live_uses_live_ecu_instead_of_old_dtc(self):
  w,s=self.window();s.navigate('diagnosis');ws=w.diagnostic_workspace
  ws.display({'id':'selection-test','vehicle':{'make':'A'},'evidence':'simulator','ecus':[{'id':'7E8','supported_pids':[12]},{'id':'7E9','supported_pids':[12]}]})
  ws.rows(ws.dtc,[['7E8','stored','ok','P0300']]);ws.dtc.selectRow(0);ws.ecus.setCurrentIndex(ws.ecus.findData('7E9'));ws.tabs.setCurrentIndex(2)
  self.assertTrue(hasattr(ws,'assistant_live_button'),'Live assistant action missing');ws.assistant_live_button.click();self.assertEqual(s.assistant_panel.context['ecu'],'7E9');self.assertEqual(s.assistant_panel.context['dtc'],'')
 def test_cloud_request_uses_separate_worker_and_preserves_snapshot(self):
  import time
  w,s=self.window();s.show_assistant();panel=s.assistant_panel;cloud=panel.cloud
  cloud.key.setText('test-only-key');cloud.prompt.setPlainText('Explain');cloud.consent.setChecked(True);cloud.approve.setChecked(True);w._obd_worker=object();original=w.task
  with patch('cloud_ai.stream_chat',return_value=iter(['Fixture explanation'])) as call:
   cloud.send();deadline=time.monotonic()+3
   while getattr(w,'cloud_task',None) is not None and time.monotonic()<deadline:self.app.processEvents();time.sleep(.01)
   call.assert_called_once();self.assertIs(w.task,original);self.assertIn('Fixture explanation',cloud.conversation.toPlainText())
  w._obd_worker=None;self.assertIn('cloud_analysis',[r['kind'] for r in panel.events()])
 def test_expand_does_not_hide_or_stop_diagnostic_page(self):
  w,s=self.window();w.resize(1600,1000);s.navigate('diagnosis');w.show();self.app.processEvents();ws=w.diagnostic_workspace;s.show_assistant();panel=s.assistant_panel
  with patch.object(ws,'stop') as stop:
   panel.toggle_expanded();self.app.processEvents();self.assertFalse(w.pages.isHidden());stop.assert_not_called();panel.toggle_expanded();self.app.processEvents();stop.assert_not_called()
 def test_notes_restore_for_session_and_clear_on_new_session(self):
  w,s=self.window();w.vehicle={'make':'Notes','vin':'session-one'};s.show_assistant();panel=s.assistant_panel;panel.symptoms.setPlainText('Cold start symptom');panel.capture()
  w2,s2=self.window();w2.vehicle=dict(w.vehicle);s2.show_assistant();panel=s2.assistant_panel;self.assertEqual(panel.symptoms.toPlainText(),'Cold start symptom')
  w2.vehicle={'make':'Notes','vin':'session-two'};panel.capture();self.assertEqual(panel.symptoms.toPlainText(),'');self.assertNotEqual(panel.context['session_id'],'')
 def test_cloud_side_panel_does_not_require_horizontal_scrolling(self):
  w,s=self.window();w.resize(1600,1000);w.show();s.show_assistant();panel=s.assistant_panel;panel.tabs.setCurrentIndex(1);self.app.processEvents()
  scroll=panel.tabs.widget(1);self.assertEqual(scroll.horizontalScrollBar().maximum(),0)
 def test_session_switch_clears_previous_cloud_answer(self):
  w,s=self.window();w.vehicle={'make':'A','vin':'one'};s.show_assistant();panel=s.assistant_panel;panel.cloud.conversation.setPlainText('Vehicle A interpretation')
  w.vehicle={'make':'B','vin':'two'};panel.capture();self.assertNotIn('Vehicle A interpretation',panel.cloud.conversation.toPlainText())
 def test_query_consent_reset_on_capture_and_edit(self):
  w,s=self.window();w.vehicle={'make':'A','vin':'one'};s.show_assistant();panel=s.assistant_panel;panel.external_consent.setChecked(True)
  w.vehicle={'make':'B','vin':'two'};panel.capture();self.assertFalse(panel.external_consent.isChecked());panel.external_consent.setChecked(True);panel.query.setPlainText('A changed query');self.assertFalse(panel.external_consent.isChecked())
 def test_opened_source_records_only_approved_redacted_note(self):
  w,s=self.window();w.vehicle={'make':'A','vin':'VF1AAAAAA12345678'};s.show_assistant();panel=s.assistant_panel;panel.symptoms.setPlainText('VIN VF1AAAAAA12345678');panel.capture();panel.symptoms.setPlainText('Edited after capture: VF1AAAAAA12345678')
  from PySide6.QtCore import QUrl
  with patch('session_assistant.QDesktopServices.openUrl',return_value=True):panel.open_source(QUrl('https://example.com/a'))
  row=next(r for r in panel.events() if r['kind']=='opened_source');self.assertNotIn('VF1AAAAAA12345678',row['payload']['note']);self.assertEqual(row['payload']['note'],panel.context['symptoms'])
