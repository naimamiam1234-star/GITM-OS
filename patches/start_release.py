"""Select the installed application release, falling back to the bundled one."""
import json, os, sys
from pathlib import Path
base=Path(__file__).resolve().parent
state=Path(os.environ.get('GITM_STATE',str(Path.home()/'.local/share/gitm')))
selected=base
try:
    current=Path(json.loads((state/'application-release.json').read_text())['current']).resolve()
    if (current == base or current.is_relative_to((state/'releases').resolve())) and (current/'native.py').is_file():
        selected=current
except (OSError, ValueError, KeyError, TypeError):
    pass
os.chdir(selected)
os.execv(sys.executable,[sys.executable,str(selected/'native.py'),*sys.argv[1:]])
