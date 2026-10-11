"""Extend actual guest gallery with clearly identified simulator results."""
def setup(w,steps,emit):
    import transport
    from obd_simulator import Simulator
    def scan():
        w.fixture=Simulator().start()
        transport.LINK.connect('wifi',f'127.0.0.1:{w.fixture.port}',family='elm')
        w.vehicle={'make':'GITM simulator','model':'Bench','engine':'SIM','year':2020}
        w.diagnosis_page();w.diagnostic_workspace.scan()
    def tab(index):
        ui=w.diagnostic_workspace
        w.pages.setCurrentWidget(ui.parentWidget())
        if not ui.report or ui.report['status']!='complete' or ui.report.get('evidence')!='simulator':raise RuntimeError('Guest simulator scan did not complete')
        if index==2:
            ui.tabs.setCurrentIndex(2);ui.pids.setCurrentIndex(ui.pids.findData(12));ui.record.setChecked(True);ui.toggle_live()
        else:
            ui.stop();ui.tabs.setCurrentIndex(index)
    def verify():
        ui=w.diagnostic_workspace
        e={x['id']:x for x in ui.report['ecus']}
        if e['7E8']['dtc']['stored']['codes']!=['P0100','P0200','P0300','P0400']:raise RuntimeError('Guest multi-frame DTC decoding failed')
        if not any(s.get('pid')==12 and s.get('value')==1726 for s in ui.samples):raise RuntimeError('Guest live data acquisition failed')
        if not ui.recorded:raise RuntimeError('Guest live recording failed')
        from diagnostic_reports import write_report,export_csv
        from pathlib import Path
        folder=Path.home()/'.local/share/gitm/bench-evidence';folder.mkdir(parents=True,exist_ok=True)
        write_report(folder/'simulator-report.html',ui.report);write_report(folder/'simulator-report.json',ui.report)
        (folder/'simulator-live.csv').write_text(export_csv(ui.recorded))
        emit('GITM_GALLERY_DIAG_BENCH|PASS|SIMULATOR|scan-multiframe-live-csv-export')
        tab(5)
    steps.extend([('diag-bench-summary',scan),('diag-bench-dtc',lambda:tab(1)),('diag-bench-live',lambda:tab(2)),('diag-bench-readiness',lambda:tab(3)),('diag-bench-freeze',lambda:tab(4)),('diag-bench-report',verify)])
