"""Overlay tested engines and wire native AutoDiag pages; fail on source drift."""
import pathlib, shutil, sys, py_compile

MODULES=('obd_session','obd_simulator','diagnostic_workspace','diagnostic_reports','ecu_workspace','ecu_scan','diagnostic_platform','professional_components','professional_ui','cockpit_dashboard','vci_workspace','adapter_registry','vehicle_workspace','vehicle_definitions','vehicle_resources','workshop_workspace','ai_workspace','assistant_core','session_assistant','instance_gate','update_workspace','business_workspace','can_workspace','support_workspace','knowledge_workspace','system_services','resource_workspace','resource_library','vehicle_history','branding','branding_controls','boot_media')
def patch_assistant_launch(code):
    helper="def apply_launch_intent(window,argv):\n    if '--assistant' in argv:\n        window.professional_shell.show_assistant()\n\n"
    if 'def apply_launch_intent(' not in code:
        if 'def main():' not in code:raise RuntimeError('Native entrypoint source drift')
        code=code.replace('def main():',helper+'def main():',1)
    marker='    w.showMaximized()\n'
    call='    apply_launch_intent(w,sys.argv)\n'
    if marker+call not in code:
        if marker not in code:raise RuntimeError('Native window startup source drift')
        code=code.replace(marker,marker+call,1)
    if 'gate=InstanceGate(store.BASE,app)' not in code:
        marker="    w = Window()\n"
        gate="""    gate=None;holder={}
    if '--secondary' not in sys.argv:
        from instance_gate import InstanceGate,dispatch_existing_tool
        gate=InstanceGate(store.BASE,app)
        def activate(argv):
            window=holder.get('window')
            if window is not None:
                apply_launch_intent(window,argv)
                dispatch_existing_tool(window,argv)
                if window.isMinimized():window.showNormal()
                else:window.show()
                window.raise_();window.activateWindow()
        if not gate.acquire(sys.argv,activate):return 0
        app.aboutToQuit.connect(gate.close)
"""
        if marker in code:code=code.replace(marker,gate+marker+"    holder['window']=w\n",1)
    return code
def patch_legacy_main(code):
    marker='    from desktop_shell import Dock\n'
    if marker not in code:return code
    start=code.index(marker,code.index('def main():'))
    end=code.index("    if '--smoke' in sys.argv:",start)
    return code[:start]+'    w.showMaximized()\n'+code[end:]
def patch_transport(code):
    if 'self.generation=0;' not in code:
        marker=' def __init__(self): self.io='
        if marker not in code:raise RuntimeError('Transport constructor source drift')
        code=code.replace(marker,' def __init__(self): self.generation=0; self.io=',1)
    marker=' def close(self):\n';generation="  self.generation = getattr(self,'generation',0)+1\n"
    if marker+generation not in code:
        if marker not in code:raise RuntimeError('Transport close source drift')
        code=code.replace(marker,marker+generation,1)
    return code
def install(target):
    target=pathlib.Path(target);source=pathlib.Path(__file__).parent
    for name in MODULES:shutil.copy2(source/(name+'.py'),target/(name+'.py'))
    shutil.copy2(source/'source_audit.json',target/'source_audit.json')
    shutil.copy2(source/'source_catalog_extension.json',target/'source_catalog_extension.json')
    p=target/'native.py';code=p.read_text()
    start=code.index('    def diagnosis_page(self):');end=code.index('    def toggle_live(self):',start)
    code=code[:start]+'''    def diagnosis_page(self):
        import diagnostic_workspace
        self.diagnostic_workspace = diagnostic_workspace.show(self)

'''+code[end:]
    start=code.index('    def engines_page(self):');end=code.index('    def reports_page(self):',start)
    code=code[:start]+'''    def engines_page(self):
        import ecu_workspace
        self.ecu_workspace = ecu_workspace.show(self)

'''+code[end:]
    marker='    def run(self, fn, out):\n'
    guard="        if getattr(self, '_obd_worker', None) is not None:\n            self.status.setText(tr('انتظر انتهاء الطلب الجاري'))\n            return\n"
    if marker+guard not in code:
        if marker not in code:raise RuntimeError('Native worker source drift')
        code=code.replace(marker,marker+guard)
    marker='        self.timer.timeout.connect(self.poll_live)\n'
    hook='        import professional_ui\n        professional_ui.install(self)\n'
    if marker+hook not in code:
        if marker not in code:raise RuntimeError('Native initialization source drift')
        code=code.replace(marker,marker+hook,1)
    p.write_text(patch_assistant_launch(patch_legacy_main(code)))
    p=target/'transport.py';p.write_text(patch_transport(p.read_text()));py_compile.compile(str(p),doraise=True)
    for name in (*MODULES,'native'):py_compile.compile(str(target/(name+'.py')),doraise=True)
    shutil.copytree(source/'vehicle-data',target/'vehicle-data',dirs_exist_ok=True)
    shutil.copy2(source/'gitm_desktop.py',target/'gitm_desktop.py')
    shutil.copy2(source/'desktop_popups.py',target/'desktop_popups.py')
    shutil.copytree(source/'assets/branding',target/'assets/branding',dirs_exist_ok=True)
    legacy=target/'assets/desktop/wallpaper.png'
    legacy.unlink(missing_ok=True);legacy.symlink_to('../branding/wallpapers/dark-09.jpg')
    shutil.copytree(source/'resources',target/'resources',dirs_exist_ok=True)
    (target/'assets/tools').mkdir(parents=True,exist_ok=True)
    shutil.copy2(source/'assets/tools/ai.svg',target/'assets/tools/ai.svg')
    shutil.copy2(source/'assistant-bench.py',target/'assistant-bench.py')
    shutil.copy2(source/'branding-bench.py',target/'branding-bench.py')
    docs=target/'diagnostic-docs';docs.mkdir(exist_ok=True)
    for name in ('SOURCES.md','SOURCES_AUDIT.md','COVERAGE.md','QUICKSTART_AR.md','ASSISTANT_AR.md','DESIGN_UPDATE_AR.md'):shutil.copy2(source/name,docs/name)
    print('GITM_DIAGNOSTIC_OVERLAY_INSTALLED',flush=True)

if __name__=='__main__':install(sys.argv[1])

