#!/usr/bin/env python3
import pathlib,subprocess,sys
for p in pathlib.Path(sys.argv[1]).glob('initrd.img-*'):
 config=(p.parent/('config-'+p.name.removeprefix('initrd.img-'))).read_text()
 entries=subprocess.check_output(['lsinitramfs',str(p)],text=True).splitlines()
 for module in ['overlay','squashfs','loop','isofs']:
  if not any('/'+module+'.ko' in item for item in entries) and ('CONFIG_'+{'overlay':'OVERLAY_FS','squashfs':'SQUASHFS','loop':'BLK_DEV_LOOP','isofs':'ISO9660_FS'}[module]+'=y') not in config:raise RuntimeError('Initramfs missing module: '+module)
 print(p.name+': verified overlay, squashfs, loop and ISO filesystem modules')
