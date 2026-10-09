#!/usr/bin/env python3
"""Boot actual BIOS/UEFI guests and wait for Qt application's visibility marker."""
import json,os,pathlib,socket,subprocess,time
root=pathlib.Path('dist').resolve();iso=root/'GITM-OS-3.2.0-integration-amd64.iso'
for mode in ['bios','uefi']:
 qmp=root/(mode+'.qmp');serial=root/(mode+'-serial.log')
 args=['qemu-system-x86_64','-accel','tcg','-machine','q35','-m','4096','-smp','2','-cdrom',str(iso),'-boot','d','-display','none','-serial','file:'+str(serial),'-qmp','unix:'+str(qmp)+',server=on,wait=off','-device','virtio-vga']
 if mode=='uefi':args+=['-drive','if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.fd']
 p=subprocess.Popen(args,stdout=subprocess.DEVNULL,stderr=(root/(mode+'-qemu.log')).open('w'))
 try:
  deadline=time.monotonic()+360
  ready=False
  while time.monotonic()<deadline:
   if p.poll() is not None:break
   if serial.exists() and 'GITM_AUTODIAG_VISIBLE' in serial.read_text(errors='replace'):ready=True;break
   time.sleep(2)
  with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as s:
   s.connect(str(qmp));f=s.makefile('rwb',buffering=0);f.readline()
   def command(v):
    f.write((json.dumps(v)+'\n').encode())
    while True:
     line=json.loads(f.readline())
     if 'return' in line or 'error' in line:return line
   command({'execute':'qmp_capabilities'})
   result=command({'execute':'screendump','arguments':{'filename':str(root/(mode+'.ppm'))}})
   if 'error' in result:raise RuntimeError(result)
  from PIL import Image
  Image.open(root/(mode+'.ppm')).save(root/(mode+'.png'));(root/(mode+'.ppm')).unlink()
  if not ready:raise RuntimeError(mode+' failed to reach visible AutoDiag within 360 seconds')
  print(mode+': actual guest reached visible AutoDiag',flush=True)
 finally:
  p.terminate()
  try:p.wait(timeout=10)
  except subprocess.TimeoutExpired:p.kill();p.wait()
