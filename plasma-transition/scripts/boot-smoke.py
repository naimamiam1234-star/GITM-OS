#!/usr/bin/env python3
"""Boot actual BIOS/UEFI guests and wait for Qt application's visibility marker."""
import json,os,pathlib,socket,subprocess,time
gallery=os.environ.get('GITM_GALLERY')=='1'
root=pathlib.Path('dist').resolve();iso=root/'GITM-OS-3.3.0-integration-amd64.iso'
if gallery:
 subprocess.run(['xorriso','-osirrox','on','-indev',str(iso),'-extract','/casper/vmlinuz',str(root/'gallery-vmlinuz'),'-extract','/casper/initrd',str(root/'gallery-initrd')],check=True)
for mode in (['bios','uefi','gallery'] if gallery else ['bios','uefi']):
 qmp=root/(mode+'.qmp');serial=root/(mode+'-serial.log')
 args=['qemu-system-x86_64','-machine','q35,accel=kvm:tcg','-cpu','max','-m','4096','-smp','2','-cdrom',str(iso),'-boot','d','-display','none','-serial','file:'+str(serial),'-qmp','unix:'+str(qmp)+',server=on,wait=off','-device','virtio-vga']
 if mode=='uefi':args+=['-drive','if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.fd']
 if mode=='gallery':args+=['-kernel',str(root/'gallery-vmlinuz'),'-initrd',str(root/'gallery-initrd'),'-append','boot=casper gitm.gallery=1 console=tty0 console=ttyS0,115200 ---']
 p=subprocess.Popen(args,stdout=subprocess.DEVNULL,stderr=(root/(mode+'-qemu.log')).open('w'))
 try:
  while not qmp.exists():
   if p.poll() is not None:raise RuntimeError('QEMU exited')
   time.sleep(.1)
  s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);s.connect(str(qmp));f=s.makefile('rwb',buffering=0);f.readline()
  def command(v):
   f.write((json.dumps(v)+'\n').encode())
   while True:
    line=json.loads(f.readline())
    if 'return' in line or 'error' in line:return line
  command({'execute':'qmp_capabilities'})
  seen=set();ready=False;deadline=time.monotonic()+(1800 if mode=='gallery' else 600)
  while time.monotonic()<deadline:
   if p.poll() is not None:break
   text=serial.read_text(errors='replace') if serial.exists() else ''
   ready='GITM_DESKTOP_VISIBLE' in text and 'GITM_PLASMA_SESSION|plasmashell 6.' in text
   if 'GITM_DESKTOP_START_FAILED|' in text:break
   if mode=='gallery':
    import re
    for name in re.findall(r'GITM_GALLERY_FRAME\|([a-z0-9-]+)',text):
     if name in seen:continue
     seen.add(name);directory=root/'gallery';directory.mkdir(exist_ok=True);ppm=directory/(name+'.ppm')
     result=command({'execute':'screendump','arguments':{'filename':str(ppm)}})
     if 'error' in result:raise RuntimeError(result)
     from PIL import Image
     Image.open(ppm).save(ppm.with_suffix('.png'));ppm.unlink();print('Gallery screenshot: '+name,flush=True)
    if 'GITM_GALLERY_DONE' in text:break
   elif ready:break
   time.sleep(1)
  if mode=='gallery':
   if 'GITM_GALLERY_DONE' not in text:raise RuntimeError('Gallery did not finish')
   if 'GITM_NETWORK_RELEASE_OK|resolute' not in text:raise RuntimeError('Gallery guest could not read the official Ubuntu repository')
   (root/'gallery'/'guest-report.txt').write_text('\n'.join(x for x in text.splitlines() if 'GITM_GALLERY_' in x or 'GITM_BROWSER_POLICY' in x or 'GITM_NETWORK_' in x))
  result=command({'execute':'screendump','arguments':{'filename':str(root/(mode+'.ppm'))}})
  if 'error' in result:raise RuntimeError(result)
  s.close()
  from PIL import Image
  Image.open(root/(mode+'.ppm')).save(root/(mode+'.png'));(root/(mode+'.ppm')).unlink()
  if not ready:
   print(serial.read_text(errors='replace')[-25000:] if serial.exists() else 'No serial log',flush=True)
   raise RuntimeError(mode+' failed to reach visible GITM desktop within 600 seconds')
  print(mode+': actual guest reached visible GITM desktop',flush=True)
 finally:
  p.terminate()
  try:p.wait(timeout=10)
  except subprocess.TimeoutExpired:p.kill();p.wait()


