"""Read model/year/engine relationships from sourced local vehicle definitions."""
import json
from pathlib import Path

def load(path):
 path=Path(path)
 if not path.exists():return []
 if path.stat().st_size>2*1024*1024:raise ValueError('Vehicle definition file exceeds 2MB')
 data=json.loads(path.read_text(encoding='utf-8'))
 if not isinstance(data,list):raise ValueError('Vehicle definitions must be a list')
 for row in data:
  if not isinstance(row,dict) or any(not isinstance(row.get(key),str) or not row[key].strip() for key in ('make','model','generation','market','source')):raise ValueError('Every definition requires make, model, generation, market and source')
  years=row.get('years')
  if not isinstance(years,list) or not years or any(type(y) is not int or y<1886 or y>2100 for y in years):raise ValueError('Explicit documented model years required')
  engines=row.get('engines')
  if not isinstance(engines,list):raise ValueError('Engine list required')
  for engine in engines:
   if not isinstance(engine,dict) or any(not isinstance(engine.get(k),str) or not engine[k].strip() for k in ('name','fuel','source')):raise ValueError('Engine name, fuel and source required')
   if not isinstance(engine.get('years'),list) or not engine['years'] or any(type(y) is not int or y not in years for y in engine['years']):raise ValueError('Engine years must belong to the selected model')
 return data

def models(rows,make):return [r for r in rows if r['make'].casefold()==make.strip().casefold()]
def engines(row,year):return [e for e in row['engines'] if year in e['years']]
