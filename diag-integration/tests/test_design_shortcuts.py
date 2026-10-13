import unittest
from unittest.mock import patch

class DesignShortcuts(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  from PySide6.QtWidgets import QApplication
  cls.app=QApplication.instance() or QApplication([])
 def test_launch_argument_opens_existing_assistant_without_navigation(self):
  import native
  w=native.Window();self.addCleanup(w.close);s=w.professional_shell
  page=w.pages.currentWidget()
  native.apply_launch_intent(w,['--assistant'])
  self.assertIs(w.pages.currentWidget(),page)
  panel=s.assistant_panel
  self.assertIsNotNone(panel)
  native.apply_launch_intent(w,['--assistant'])
  self.assertIs(s.assistant_panel,panel)
 def test_home_actions_route_to_real_pages_and_assistant(self):
  import native
  w=native.Window();self.addCleanup(w.close);s=w.professional_shell
  self.assertIn('vehicle',s.home_actions)
  s.home_actions['vehicle'].click()
  self.assertEqual(s.current,'vehicle')
  s.home();page=w.pages.currentWidget();s.home_actions['ai'].click()
  self.assertIs(w.pages.currentWidget(),page)
  self.assertIsNotNone(s.assistant_panel)
 def test_desktop_assistant_uses_same_application_process_key(self):
  import gitm_desktop
  from types import SimpleNamespace
  with patch.object(gitm_desktop.Desktop,'launch') as launch:
   gitm_desktop.Desktop.activate(SimpleNamespace(launch=launch),'assistant')
  self.assertEqual(launch.call_args.args[0],'autodiag')
  self.assertIn('--assistant',launch.call_args.args[1])
 def test_running_desktop_request_opens_assistant_once(self):
  import native,store
  w=native.Window();self.addCleanup(w.close);s=w.professional_shell
  with patch.object(store,'cache',return_value={'id':'request-1','action':'assistant'}):
   s.refresh();panel=s.assistant_panel
   self.assertIsNotNone(panel)
   panel.hide();s.refresh()
   self.assertTrue(panel.isHidden())
 def test_overlay_installs_launch_intent_on_baseline_idempotently(self):
  import importlib.util
  from pathlib import Path
  spec=importlib.util.spec_from_file_location('overlay_install',Path(__file__).parents[1]/'install.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  baseline="def main():\n    w.showMaximized()\n    return app.exec()\n"
  code=module.patch_assistant_launch(baseline)
  self.assertIn('apply_launch_intent(w,sys.argv)',code)
  self.assertEqual(code,module.patch_assistant_launch(code))
