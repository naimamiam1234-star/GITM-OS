#!/usr/bin/env python3
"""Boot only a fresh virtual disk, collect startup screenshots and serial evidence."""
import base64, json, pathlib, re, socket, subprocess, sys, time
from PIL import Image
iso=pathlib.Path(sys.argv[1]).resolve(); root=pathlib.Path('dist/install-probe').resolve()
root.mkdir(parents=True,exist_ok=True)
disk=root/'test-only-40GiB.qcow2'; baseline=root/'blank-baseline.qcow2'
if disk.exists(): raise RuntimeError('Refusing reuse of an existing test disk')
subprocess.run(['qemu-img','create','-f','qcow2',str(disk),'40G'],check=True)
subprocess.run(['cp',str(disk),str(baseline)],check=True)
qmp=root/'probe.qmp'; serial=root/'serial.log'
args=['qemu-system-x86_64','-machine','q35,accel=kvm:tcg','-cpu','max','-m','6144','-smp','2',
      '-cdrom',str(iso),'-drive','file='+str(disk)+',format=qcow2,if=virtio',
      '-kernel',str(root/'vmlinuz'),'-initrd',str(root/'initrd'),
      '-append','boot=casper console=tty0 console=ttyS0,115200 ---',
      '-display','none','-serial','file:'+str(serial),'-qmp','unix:'+str(qmp)+',server=on,wait=off',
      '-device','virtio-vga','-nic','user,model=virtio-net-pci']
(root/'qemu-command.json').write_text(json.dumps(args,indent=2))
p=subprocess.Popen(args,stdout=subprocess.DEVNULL,stderr=(root/'qemu.log').open('w'))
try:
 deadline=time.monotonic()+1200
 while not qmp.exists():
  if p.poll() is not None or time.monotonic()>deadline: raise RuntimeError('QEMU not ready')
  time.sleep(.1)
 s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM); s.connect(str(qmp)); f=s.makefile('rwb',buffering=0); f.readline()
 def command(v):
  f.write((json.dumps(v)+'\n').encode())
  while True:
   line=json.loads(f.readline())
   if 'return' in line or 'error' in line: return line
 command({'execute':'qmp_capabilities'}); seen=set(); text=''
 while time.monotonic()<deadline and p.poll() is None:
  text=serial.read_text(errors='replace') if serial.exists() else ''
  for label in re.findall(r'GITM_INSTALL_PROBE\|FRAME\|([a-z-]+)',text):
   if label in seen: continue
   seen.add(label); ppm=root/(label+'.ppm')
   result=command({'execute':'screendump','arguments':{'filename':str(ppm)}})
   if 'error' in result: raise RuntimeError(result)
   Image.open(ppm).save(ppm.with_suffix('.png')); ppm.unlink()
  if 'GITM_INSTALL_PROBE|DONE' in text: break
  time.sleep(1)
 else: raise RuntimeError('Guest probe did not finish')
 chunks=re.findall(r'GITM_INSTALL_PROBE\|DATA\|([A-Za-z0-9+/=]+)',text)
 if not chunks or 'GITM_INSTALL_PROBE|ARCHIVE_END' not in text: raise RuntimeError('Missing guest archive')
 (root/'guest-evidence.tar.gz').write_bytes(base64.b64decode(''.join(chunks),validate=True))
 (root/'markers.txt').write_text('\n'.join(x for x in text.splitlines() if 'GITM_INSTALL_PROBE|' in x and '|DATA|' not in x))
 print((root/'markers.txt').read_text(),flush=True)
finally:
 p.terminate()
 try: p.wait(timeout=10)
 except subprocess.TimeoutExpired: p.kill(); p.wait()
compare=subprocess.run(['qemu-img','compare',str(baseline),str(disk)],capture_output=True,text=True)
(root/'disk-unchanged.txt').write_text(compare.stdout+compare.stderr+'exit='+str(compare.returncode)+'\n')
if compare.returncode: raise RuntimeError('Startup-only probe changed virtual disk content')
