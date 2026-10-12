"""Overlay tested engines and wire native AutoDiag pages; fail on source drift."""
import pathlib, shutil, sys, py_compile

MODULES=('obd_session','obd_simulator','diagnostic_workspace','diagnostic_reports','ecu_workspace','ecu_scan','diagnostic_platform','professional_components','professional_ui','vci_workspace','vehicle_workspace','workshop_workspace','ai_workspace','update_workspace','business_workspace','can_workspace','support_workspace','knowledge_workspace','system_services','resource_workspace')
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
    p.write_text(code)
    p=target/'transport.py';p.write_text(patch_transport(p.read_text()));py_compile.compile(str(p),doraise=True)
    for name in (*MODULES,'native'):py_compile.compile(str(target/(name+'.py')),doraise=True)
    docs=target/'diagnostic-docs';docs.mkdir(exist_ok=True)
    for name in ('SOURCES.md','COVERAGE.md','QUICKSTART_AR.md'):shutil.copy2(source/name,docs/name)
    print('GITM_DIAGNOSTIC_OVERLAY_INSTALLED',flush=True)

if __name__=='__main__':install(sys.argv[1])
