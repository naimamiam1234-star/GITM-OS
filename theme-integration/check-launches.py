"""Exercise launch routing without starting or modifying the host desktop."""
import importlib.util,sys,types
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path('output/GITM-OS-3.3/app').resolve()))
spec=importlib.util.spec_from_file_location('desktop_under_test','plasma-transition/patches/gitm_desktop.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
calls=[]
class FakeProcess:
 NotRunning=0
 def __init__(self,parent):self.running=0;self.argv=[];self.errorOccurred=self.finished=types.SimpleNamespace(connect=lambda f:None)
 def state(self):return self.running
 def setProcessEnvironment(self,e):self.environment=e
 def setProgram(self,p):self.program=p
 def setArguments(self,a):self.argv=a
 def setWorkingDirectory(self,p):pass
 def setStandardErrorFile(self,*a):pass
 def startDetached(self):return True,42
 def start(self):self.running=1;calls.append((self.program,self.argv))
host=types.SimpleNamespace(processes={})
with patch.object(m,'QProcess',FakeProcess),patch.object(m.shutil,'which',side_effect=lambda name:None if name=='wmctrl' else '/usr/bin/'+name):
 for key,args in [('settings',['systemsettings']),('display',['systemsettings','kcm_kscreen']),('power-settings',['systemsettings','kcm_powerdevilprofilesconfig']),('all-settings',['systemsettings'])]:m.Desktop.launch(host,key,args)
 assert len(calls)==1,calls
 assert list(host.processes)==['settings'],host.processes
 assert host.processes['settings'].environment.value('QT_STYLE_OVERRIDE')==''
 m.Desktop.launch(host,'calculator',['kcalc'])
 assert calls[-1]==('kcalc',[]),calls
print('Repeated settings entry points start one process; calculator starts native KCalc')
