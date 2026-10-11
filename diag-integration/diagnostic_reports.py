"""Offline exports preserving observed data and acquisition errors."""
import csv, io, json
from pathlib import Path
from html import escape

def export_csv(samples):
 out=io.StringIO();writer=csv.DictWriter(out,fieldnames=['session_id','vehicle','evidence','at','ecu','pid','name','value','unit','error'],extrasaction='ignore');writer.writeheader()
 for sample in samples:
  row=dict(sample)
  if isinstance(row.get('vehicle'),dict):row['vehicle']=json.dumps(row['vehicle'],ensure_ascii=False,sort_keys=True)
  writer.writerow(row)
 return out.getvalue()

def html_report(report):
 def e(value):return escape(str(value if value is not None else 'Unavailable'))
 def table(headers,rows):
  return '<table><thead><tr>'+''.join('<th>'+e(h)+'</th>' for h in headers)+'</tr></thead><tbody>'+(''.join('<tr>'+''.join('<td>'+e(v)+'</td>' for v in row)+'</tr>' for row in rows) or '<tr><td colspan="'+str(len(headers))+'">No observations available</td></tr>')+'</tbody></table>'
 sections=[]
 if report.get('evidence')=='simulator':sections.append('<aside><strong>SIMULATOR</strong> · Bench simulation only. This report is not evidence of a physical vehicle test.</aside>')
 vehicle=report.get('vehicle') or {}
 sections.append('<h2>Session identity</h2>'+table(['Field','Observation'],[[k,report.get(k)] for k in ('id','status','started_at','finished_at','protocol','scope','adapter_identity','evidence')]+[['Vehicle '+str(k),v] for k,v in vehicle.items()]))
 for ecu in report.get('ecus',[]):
  sections.append('<h2>ECU '+e(ecu.get('id',''))+'</h2><p>VIN: '+e(ecu.get('vin'))+'</p>')
  dtcs=[]
  for kind,result in (ecu.get('dtc') or {}).items():
   for code in result.get('codes',[]) or ['None reported' if result.get('status')=='ok' else 'Unavailable']:dtcs.append([kind,result.get('status'),code,result.get('error','')])
  sections.append('<h3>Diagnostic trouble codes</h3>'+table(['Class','Acquisition','Code','Error'],dtcs))
  ready=ecu.get('readiness') or {}
  sections.append('<h3>Readiness</h3><p>MIL: '+e(ready.get('MIL'))+' · Stored DTC count: '+e(ready.get('stored_dtc_count'))+' · Engine type: '+e(ready.get('engine_type'))+'</p>'+table(['Monitor','Supported','Complete'],[[m.get('name'),m.get('supported'),m.get('complete')] for m in ready.get('monitors',[])]))
  frame=ecu.get('freeze') or {}
  sections.append('<h3>Freeze frame '+e(frame.get('frame'))+'</h3><p>Trigger DTC: '+e(', '.join(frame.get('trigger_dtc',[])))+'</p>'+table(['PID','Parameter','Value','Unit'],[[v.get('pid'),v.get('name'),v.get('value'),v.get('unit')] for v in frame.get('values',[])]))
  if ecu.get('errors'):sections.append('<h3>ECU acquisition errors</h3><ul>'+''.join('<li>'+e(error)+'</li>' for error in ecu['errors'])+'</ul>')
 if report.get('clear_action'):
  action=report['clear_action'];sections.append('<h2>Clear operation</h2>'+table(['Field','Observation'],[[k,action.get(k)] for k in ('before_id','status','scope','acknowledgements')]))
  if action.get('trace'):sections.append('<details><summary>Clear operation trace</summary>'+table(['Time','Command','Response'],[[r.get('at'),r.get('command'),r.get('response')] for r in action['trace']])+'</details>')
 if report.get('live'):
  fields=['session_id','vehicle','evidence','at','ecu','pid','name','value','unit','error'];sections.append('<h2>Live observations</h2>'+table(['Session','Vehicle','Evidence','Time','ECU','PID','Parameter','Value','Unit','Error'],[[r.get(k,'') for k in fields] for r in report['live'][:10000]]))
 sections.append('<details open><summary>Acquisition errors</summary>'+table(['ECU','Section','Error'],[[r.get('ecu',''),r.get('section'),r.get('error')] for r in report.get('errors',[])])+'</details>')
 sections.append('<details><summary>Command trace</summary>'+table(['Time','Command','Response'],[[r.get('at'),r.get('command'),r.get('response')] for r in report.get('trace',[])])+'</details>')
 return '<!doctype html><html><head><meta charset="utf-8"><title>OBD diagnostic report</title><style>body{font:16px sans-serif;max-width:1000px;margin:40px auto;color:#16283b;padding:0 24px}table{width:100%;border-collapse:collapse;margin:14px 0}th,td{text-align:left;border:1px solid #cbd5e1;padding:10px;overflow-wrap:anywhere}th{background:#edf2f7}h2{border-top:2px solid #abc;padding-top:20px}aside{background:#fff4d6;padding:18px;border:2px solid #d97706}summary{cursor:pointer;font-weight:bold;margin:18px 0}</style></head><body><h1>OBD diagnostic report</h1><p>Generic emissions OBD only. Observations do not establish a component failure.</p>'+''.join(sections)+'</body></html>'

def write_report(path,report):
 path=Path(path)
 if path.suffix.lower()=='.html':data=html_report(report)
 elif path.suffix.lower()=='.csv':data=export_csv(report.get('live',[]))
 elif path.suffix.lower()=='.json':data=json.dumps(report,ensure_ascii=False,indent=2)
 else:raise ValueError('Choose .json, .html or .csv')
 path.write_text(data,encoding='utf-8')
