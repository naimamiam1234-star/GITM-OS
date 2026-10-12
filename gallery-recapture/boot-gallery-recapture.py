#!/usr/bin/env python3
"""Execute an ephemeral boot-smoke copy with the gallery-only initrd override."""
import os,pathlib,subprocess,sys
base=pathlib.Path(__file__).resolve().parent
source=pathlib.Path('plasma-fix/boot-smoke.py').read_text()
anchor="for mode in (['bios','uefi','gallery'] if gallery else ['bios','uefi']):"
if source.count(anchor)!=1:raise RuntimeError('Cannot locate shipped boot-smoke gallery preparation boundary')
hook="if gallery:\n subprocess.run([sys.executable, "+repr(str(base/'inject-gallery.py'))+",str(iso),str(root/'gallery-initrd'),str(root/'gallery-initrd')],check=True)\n"
patched='import sys\n'+source.replace(anchor,hook+anchor)
compile(patched,'fixture-boot-smoke.py','exec')
root=pathlib.Path('dist');root.mkdir(exist_ok=True);driver=root/'fixture-boot-smoke.py';driver.write_text(patched)
env=os.environ.copy();env['GITM_GALLERY']='1'
subprocess.run([sys.executable,str(driver)],env=env,check=True)
serial=(root/'gallery-serial.log').read_text(errors='replace')
if 'GITM_GALLERY_INSTALLER_MINIMIZED|' not in serial or 'GITM_GALLERY_INSTALLER_HIDDEN|PASS' not in serial:raise RuntimeError('Missing fixture installer minimization/visibility proof')
if 'GITM_GALLERY_ERROR|' in serial:raise RuntimeError('Guest gallery errors remain; inspect serial evidence')
if len(list((root/'gallery').glob('*.png')))!=69:raise RuntimeError('Expected exactly 69 gallery captures')
