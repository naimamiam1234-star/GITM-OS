#!/usr/bin/env python3
"""Install to a fresh fixture then boot the same disk with all live media removed."""
import base64,json,pathlib,re,socket,subprocess,sys,time
from PIL import Image
root=pathlib.Path('dist/disk-install').resolve(); root.mkdir(parents=True,exist_ok=True)
iso=pathlib.Path(sys.argv[1]).resolve(); disk=root/'test-only-40GiB.qcow2'
if disk.exists(): raise RuntimeError('Refusing an existing fixture disk')
subprocess.run(['qemu-img','create','-f','qcow2',str(disk),'40G'],check=True)

def boot(stage,live):
    qmp=root/(stage+'.qmp'); serial=root/(stage+'-serial.log')
    args=['qemu-system-x86_64','-machine','q35,accel=kvm:tcg','-cpu','max','-m','6144','-smp','2',
          '-drive','file='+str(disk)+',format=qcow2,if=none,id=install-disk',
          '-device','virtio-blk-pci,drive=install-disk,serial=GITM-CI-ONLY',
          '-display','none','-serial','file:'+str(serial),'-qmp','unix:'+str(qmp)+',server=on,wait=off',
          '-device','virtio-vga','-nic','user,model=virtio-net-pci','-no-reboot']
    if live: args+=['-cdrom',str(iso),'-kernel',str(root/'vmlinuz'),'-initrd',str(root/'initrd'),'-append','boot=casper console=tty0 console=ttyS0,115200 ---']
    else: args+=['-boot','c']
    (root/(stage+'-command.json')).write_text(json.dumps(args,indent=2))
    p=subprocess.Popen(args,stdout=subprocess.DEVNULL,stderr=(root/(stage+'-qemu.log')).open('w'))
    s=None; text=''; seen=set(); success='INSTALL_PASS' if live else 'DISK_BOOT_PASS'
    deadline=time.monotonic()+(2400 if live else 900)
    try:
        while True:
            if p.poll() is not None or time.monotonic()>deadline:
                raise RuntimeError('QEMU failed to start: '+(root/(stage+'-qemu.log')).read_text())
            s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM); s.settimeout(30)
            try:
                s.connect(str(qmp)); break
            except (FileNotFoundError, ConnectionRefusedError):
                s.close(); s=None; time.sleep(.2)
        f=s.makefile('rwb',buffering=0); f.readline()
        def command(v):
            f.write((json.dumps(v)+'\n').encode())
            while True:
                r=json.loads(f.readline())
                if 'return' in r or 'error' in r: return r
        command({'execute':'qmp_capabilities'})
        while time.monotonic()<deadline:
            text=serial.read_text(errors='replace') if serial.exists() else ''
            for label in re.findall(r'GITM_INSTALL_TEST\|FRAME\|([a-z-]+)',text):
                if label in seen: continue
                seen.add(label); ppm=root/(stage+'-'+label+'.ppm')
                r=command({'execute':'screendump','arguments':{'filename':str(ppm)}})
                if 'error' in r: raise RuntimeError(r)
                Image.open(ppm).save(ppm.with_suffix('.png')); ppm.unlink()
            if 'GITM_INSTALL_TEST|ARCHIVE_END' in text:
                chunks=re.findall(r'GITM_INSTALL_TEST\|DATA\|([A-Za-z0-9+/=]+)',text)
                (root/(stage+'-guest-evidence.tar.gz')).write_bytes(base64.b64decode(''.join(chunks),validate=True))
            if 'GITM_INSTALL_TEST|ERROR|' in text and 'GITM_INSTALL_TEST|ARCHIVE_END' in text: raise RuntimeError(stage+' guest failed; see serial and archive')
            if 'GITM_INSTALL_TEST|'+success in text: return
            if p.poll() is not None: raise RuntimeError(stage+' VM exited before pass')
            time.sleep(.5)
        raise RuntimeError(stage+' timed out')
    finally:
        (root/(stage+'-markers.txt')).write_text('\n'.join(l for l in text.splitlines() if 'GITM_INSTALL_TEST|' in l and '|DATA|' not in l))
        if s: s.close()
        p.terminate()
        try: p.wait(timeout=10)
        except subprocess.TimeoutExpired: p.kill(); p.wait()
        if qmp.exists(): qmp.unlink()
boot('live-install',True)
boot('disk-boot',False)
(root/'result.json').write_text(json.dumps({'install':'pass','disk_boot':'pass','boot_mode':'BIOS','disk_bytes':40*1024**3,'live_media_removed':True},indent=2))
print('PASS: installation completed and native Plasma booted with / on the installed vda partition')
