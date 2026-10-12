"""Apply isolated Plasma 6 changes to the assembled application."""
from pathlib import Path
import shutil

root = Path(__file__).resolve().parent.parent
app = root / 'build-input/app'
shutil.copy2(root / 'plasma-transition/patches/gitm_desktop.py', app / 'gitm_desktop.py')
for path in app.rglob('*.py'):
    source = path.read_text()
    source = source.replace('systemsettings5', 'systemsettings')
    # Gallery cleanup must never close the native shell or its panels.
    if 'wmctrl' in source and "if 'GITM OS' not in x" in source:
        source = source.replace("if 'GITM OS' not in x", "if 'GITM OS' not in x and x.split()[2] not in subprocess.run(['pgrep','-x','plasmashell'],capture_output=True,text=True).stdout.split()")
    path.write_text(source)
