import tempfile,unittest,json
from pathlib import Path
class BrandingTests(unittest.TestCase):
 def test_theme_defaults_and_personal_wallpaper(self):
  import branding
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'wallpapers').mkdir();(root/'wallpapers/light.jpg').write_bytes(b'image');(root/'wallpapers/dark.jpg').write_bytes(b'image')
   (root/'manifest.json').write_text(json.dumps({'defaults':{'light':'wallpapers/light.jpg','dark':'wallpapers/dark.jpg'},'wallpapers':[{'path':'wallpapers/light.jpg','mode':'light'},{'path':'wallpapers/dark.jpg','mode':'dark'},{'path':'../outside.jpg','mode':'dark'}]}))
   self.assertEqual(branding.default_wallpaper('light',root),root/'wallpapers/light.jpg')
   personal=root/'personal.jpg';personal.write_bytes(b'custom')
   self.assertEqual(branding.resolve_wallpaper('dark',personal,root),personal)
   self.assertEqual(len(branding.wallpaper_choices(root)),2)
 def test_intro_can_be_skipped_and_honors_reduced_motion(self):
  import branding
  self.assertTrue(branding.should_play_intro([],{}))
  for argv,prefs in [(['--smoke'],{}),(['--skip-intro'],{}),([] ,{'reduce_motion':True}),([] ,{'performance':True}),([] ,{'boot_video':False})]:
   self.assertFalse(branding.should_play_intro(argv,prefs))

 def test_migrate_only_the_known_bundled_wallpaper(self):
  import branding
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)/'assets/branding'
   self.assertTrue(branding.is_legacy_wallpaper(Path(d)/'assets/desktop/wallpaper.png',root))
   self.assertFalse(branding.is_legacy_wallpaper(Path(d)/'my-wallpaper.png',root))

 def test_current_wallpaper_choice_is_not_legacy_when_linked(self):
  import branding
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)/'assets/branding';root.mkdir(parents=True);current=root/'dark.jpg';current.write_bytes(b'photo');old=root.parent/'desktop/wallpaper.png';old.parent.mkdir();old.symlink_to(current)
   self.assertTrue(branding.is_legacy_wallpaper(old,root));self.assertFalse(branding.is_legacy_wallpaper(current,root))
