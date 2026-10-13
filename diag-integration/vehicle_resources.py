"""Bundled brand assets and vPIC model names; never infer years or engines."""
import json
from pathlib import Path
ROOT=Path(__file__).parent/'vehicle-data'
def read(name):
 path=ROOT/name
 if not path.exists():return []
 if path.stat().st_size>2*1024*1024:raise ValueError('Vehicle resource index exceeds 2MB')
 rows=json.loads(path.read_text(encoding='utf-8'))
 if not isinstance(rows,list):raise ValueError('Vehicle resource index must be a list')
 return rows
def logos():
 output={}
 for row in read('brands.json'):
  path=(ROOT/row['path']).resolve()
  if not path.is_relative_to(ROOT.resolve()) or not path.is_file():continue
  output[row['name']]={'resolved_path':str(path),'source':'https://github.com/vehiclespecs/brand-logos','license':'Logo trademark rights; repository license excludes image ownership'}
 return output
def models(make):
 return [row for row in read('models.json') if row['make'].casefold()==str(make).strip().casefold()]
