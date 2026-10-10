import runpy,json
from pathlib import Path
scope=runpy.run_path(str(Path(__file__).with_name('check-status.py')))
w=scope['w'];app=scope['app'];desktop=scope['gitm_desktop']
w.resize(1280,800)
calls=[];original=w.launch
w.launch=lambda key,command:calls.append((key,command))
before=len(w.dialogs)
w.settings();w.choose_appearance();w.settings()
assert len(w.dialogs)==before,'Native settings must not create custom duplicate dialogs'
assert all(key=='settings' and command[0]=='systemsettings' for key,command in calls)
w.launch=original
w.appearance.update(mode='light',performance=True,reduce_motion=True)
w.save_appearance();app.processEvents()
assert json.loads((desktop.STATE/'appearance.json').read_text())['mode']=='light'
assert w.blurred.isNull()
w.grab().save(str(Path(__file__).with_name('desktop-light.png')))
w.appearance['mode']='dark';w.save_appearance();app.processEvents()
w.grab().save(str(Path(__file__).with_name('desktop-dark.png')))
other=desktop.Desktop();assert other.appearance['mode']=='dark' and other.appearance['performance']
print('APPEARANCE_PERSISTENCE_AND_NATIVE_SETTINGS_ROUTES_PASSED')
