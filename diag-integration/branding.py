"""Local brand assets and explicit wallpaper preferences; no network or telemetry."""
import json,os
from pathlib import Path
ROOT=Path(__file__).parent/'assets/branding'
def manifest(root=None):
 try:return json.loads(((root or ROOT)/'manifest.json').read_text(encoding='utf-8'))
 except (OSError,ValueError):return {}
def asset(relative,root=None):
 root=(root or ROOT).resolve();path=(root/str(relative)).resolve()
 return path if path.is_relative_to(root) and path.is_file() else None
def default_wallpaper(mode,root=None):return asset(manifest(root).get('defaults',{}).get(mode,''),root)
def resolve_wallpaper(mode,personal=None,root=None):
 if personal and Path(personal).is_file():return Path(personal)
 return default_wallpaper(mode,root)
def wallpaper_choices(root=None):
 return [dict(row,file=asset(row.get('path',''),root)) for row in manifest(root).get('wallpapers',[]) if asset(row.get('path',''),root)]
def session_clip(mode,root=None):return asset(manifest(root).get('clips',{}).get(mode,''),root)
def should_play_intro(argv,prefs):
 return not any(flag in argv for flag in ('--smoke','--skip-intro')) and prefs.get('boot_video',True) is not False and not prefs.get('reduce_motion') and not prefs.get('performance')
def symbol_pixmap(size=40):
 from PySide6.QtCore import Qt
 from PySide6.QtGui import QPixmap
 pix=QPixmap(str(ROOT/'symbol.png'))
 if pix.isNull():return pix
 return pix.copy(164,102,184,184).scaled(size,size,Qt.KeepAspectRatio,Qt.SmoothTransformation)
def brand_icon():
 from PySide6.QtGui import QIcon
 return QIcon(symbol_pixmap(128))

def is_legacy_wallpaper(path,root=None):
 return os.path.abspath(path)==os.path.abspath((root or ROOT).parent/"desktop/wallpaper.png")
