"""Regression checks for the launch/layout defects shown in the user's screenshots."""
from pathlib import Path
import ast
p=Path('plasma-transition/patches/gitm_desktop.py');s=p.read_text();tree=ast.parse(s)
methods={node.name:node for node in ast.walk(tree) if isinstance(node,ast.FunctionDef)}
settings=ast.get_source_segment(s,methods['settings'])
assert "self.panel(" not in settings, 'Settings must not open a second custom dialog'
assert "self.launch('settings',['systemsettings'])" in settings
appearance=ast.get_source_segment(s,methods['choose_appearance'])
assert "self.panel(" not in appearance
assert "if argv[0]=='systemsettings':key='settings'" in s
layout=Path('theme-integration/layout.js').read_text()
assert 'systemtray' not in layout and 'digitalclock' not in layout
assert "dock.floating = true" in layout and "dock.hiding = 'none'" in layout
assert "dock.lengthMode = 'fit'" in layout
assert 'LookAndFeelPackage=org.gitm.desktop' in Path('theme-integration/install-root.sh').read_text()
print('Settings launch paths unified; dock layout regression checks passed')
