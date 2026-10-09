#!/usr/bin/env python3
import pathlib,shutil
root=pathlib.Path('build-input/app')
def edit(name,old,new):
 p=root/name;s=p.read_text()
 if old not in s:raise RuntimeError('Source drift: '+name)
 p.write_text(s.replace(old,new))
edit('cloud_backend.py',"if not path.startswith('/v1/') and path!='/health':raise ValueError('Unknown backend route')","if path.split('?',1)[0] not in ('/health','/v1/auth/login','/v1/models','/v1/ai/chat','/v1/search','/v1/videos','/v1/vehicle/vin','/v1/providers/status'):raise ValueError('Unknown backend route')")
edit('cloud_backend.py',"if path!='/health' and not token:","if path.split('?',1)[0] not in ('/health','/v1/auth/login') and not token:")
shutil.copy('patches/cloud_ui.py',root/'cloud_ui.py')
p=root/'native.py';s=p.read_text();a=s.index('    def ai_page(self):');b=s.index('    def ask_ai(',a)
s=s[:a]+"    def ai_page(self):\n        import cloud_ui\n        cloud_ui.show(self)\n\n"+s[b:]
s=s.replace("Qt.FramelessWindowHint)","Qt.Window)")
s=s.replace("tr('انتهى الطلب · ') + str(transport.LINK.info())","tr('المحول متصل') if transport.LINK.info().get('connected') else tr('المحول غير متصل')")
s=s.replace("3.1.0-rc1","3.2.0-integration")
a=s.index('    from desktop_shell import Dock',s.index('def main():'));b=s.index("    if '--smoke' in sys.argv:",a)
s=s[:a]+'''    w.showMaximized()
    if '--tool' in sys.argv:
        key=sys.argv[sys.argv.index('--tool')+1]
        import workshop_tools
        tools={'customers':workshop_tools.customers,'invoice':workshop_tools.invoices,'camera':workshop_tools.camera,'pdf':workshop_tools.pdf,'music':workshop_tools.media,'update':workshop_tools.updates}
        if key in tools:tools[key](w)
    def boot_marker():
        if w.isVisible():
            # Guest boot verification reads this marker, not fabricated telemetry.
            __import__('subprocess').run(['logger','-t','gitm','GITM_AUTODIAG_VISIBLE'],check=False)
    QTimer.singleShot(4000,boot_marker)
'''+s[b:]
s=s.replace('        transport.LINK.close()','        if getattr(self,"cloud_task",None) is not None and self.cloud_task.isRunning():\n            event.ignore();return\n        transport.LINK.close()')
p.write_text(s)
edit('visual_theme.py','s=min(g.width()/1672,g.height()/941)','s=max(0.7,min(g.width()/1672,g.height()/941))')
edit('visual_theme.py','3.1.0-rc1','3.2.0-integration')
p=root/'system_settings.py';s=p.read_text();a=s.index('    tools={',s.index('def launch('));b=s.index("    if name not in tools",a)
s=s[:a]+'''    tools={'network':['nm-connection-editor'],'bluetooth':['systemsettings5','kcm_bluetooth'],
           'sound':['systemsettings5','kcm_pulseaudio'],'display':['systemsettings5','kcm_kscreen'],
           'power':['systemsettings5','powerdevilprofilesconfig'],'lock':['loginctl','lock-session'],
           'accounts':['systemsettings5','kcm_users'],'password':['systemsettings5','kcm_users'],
           'accessibility':['systemsettings5','kcmaccess'],'files':['dolphin'],
           'gallery':['gwenview'],'keyboard':['onboard'],'tasks':['plasma-systemmonitor'],
           'printers':['system-config-printer'],'firewall':['gufw'],'disks':['gnome-disks'],
           'packages':['plasma-discover']}
'''+s[b:]
s=s.replace("if name=='password':","if False:")
s=s.replace("executables={'display':", "executables={'display':")
# Capability gating uses actual command availability, preserving unavailable states.
a=s.index('        executables=');b=s.index('\n',a)
s=s[:a]+"        executables={'display':'systemsettings5','lock':'loginctl','files':'dolphin','gallery':'gwenview','tasks':'plasma-systemmonitor','accounts':'systemsettings5','network':'nm-connection-editor','bluetooth':'systemsettings5','sound':'systemsettings5','power':'systemsettings5','accessibility':'systemsettings5','keyboard':'onboard','printers':'system-config-printer','firewall':'gufw','disks':'gnome-disks','packages':'plasma-discover'}"+s[b:]
p.write_text(s)
p=root/'workshop_tools.py';s=p.read_text().replace('firefox-esr','falkon').replace('pcmanfm','dolphin').replace('calamares-install-debian','gitm-install');p.write_text(s)
# Keep original update trust; no fabricated replacement signing key.
edit('device_admin.py',"['/usr/bin/sudo','-n','/usr/local/sbin/gitm-device-admin'","['/usr/bin/pkexec','/usr/local/sbin/gitm-device-admin'")
print('Source integration patches applied')
