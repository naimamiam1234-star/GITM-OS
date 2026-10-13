import unittest,tempfile
from pathlib import Path
import store,knowledge
class EvidenceScope(unittest.TestCase):
 def test_other_engine_or_vehicle_never_matches(self):
  previous=store.BASE
  with tempfile.TemporaryDirectory() as directory:
   store.BASE=Path(directory)
   try:
    vehicle=dict(make='Renault',model='Megane',year=2024,engine='diesel')
    knowledge.import_document(dict(source='fixture',license='fixture',version='1',date='2026-10-13',language='ar',text='fixture',vehicle=vehicle,kind='wiring_diagram'))
    self.assertEqual(knowledge.evidence(vehicle)[0]['kind'],'wiring_diagram')
    for change in [dict(model='Clio'),dict(year=2025),dict(engine='electric'),dict(engine='')]:
     self.assertEqual(knowledge.evidence(dict(vehicle,**change)),[])
    self.assertEqual(knowledge.evidence({}),[])
   finally:store.BASE=previous
