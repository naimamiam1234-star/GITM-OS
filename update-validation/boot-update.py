#!/usr/bin/env python3
"""Install to a fresh fixture then boot the same disk with all live media removed."""
import argparse,base64,json,pathlib,re,shutil,socket,subprocess,time
from PIL import Image
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('iso',type=pathlib.Path)
parser.add_argument('--uefi',action='store_true',help='Use standard OVMF with persistent fixture-only NVRAM')
parser.add_argument('--output-root',type=pathlib.Path,default=pathlib.Path('dist/disk-install'),help='Isolated directory containing prepared vmlinuz/initrd and new fixture disk')
options=parser.parse_args()
root=options.output_root.resolve(); root.mkdir(parents=True,exist_ok=True)
iso=options.iso.resolve(); disk=root/'test-only-40GiB.qcow2'
firmware_args=[]
if options.uefi:
    code=pathlib.Path('/usr/share/OVMF/OVMF_CODE_4M.fd')
    template=pathlib.Path('/usr/share/OVMF/OVMF_VARS_4M.fd')
    nvram=root/'test-only-OVMF_VARS_4M.fd'
    if not code.is_file() or not template.is_file(): raise RuntimeError('Standard OVMF 4M firmware is missing; install ovmf')
    if nvram.exists(): raise RuntimeError('Refusing reuse of fixture NVRAM')
    shutil.copyfile(template,nvram)
    firmware_args=['-drive','if=pflash,format=raw,unit=0,readonly=on,file='+str(code),
                   '-drive','if=pflash,format=raw,unit=1,file='+str(nvram)]
if disk.exists(): raise RuntimeError('Refusing an existing fixture disk')
subprocess.run(['qemu-img','create','-f','qcow2',str(disk),'40G'],check=True)

def boot(stage,live):
    qmp=root/(stage+'.qmp'); serial=root/(stage+'-serial.log'); evidence=root/(stage+'-evidence.log')
    args=['qemu-system-x86_64','-machine','q35,accel=kvm:tcg','-cpu','max','-m','6144','-smp','2',
          '-drive','file='+str(disk)+',format=qcow2,if=none,id=install-disk',
          '-device','virtio-blk-pci,drive=install-disk,serial=GITM-CI-ONLY',
          '-display','none','-serial','file:'+str(serial),'-qmp','unix:'+str(qmp)+',server=on,wait=off',
          '-chardev','file,id=evidence,path='+str(evidence),
          '-device','virtio-serial-pci',
          '-device','virtserialport,chardev=evidence,name=gitm-test-evidence',
          '-device','virtio-vga','-nic','user,model=virtio-net-pci','-no-reboot']
    args+=firmware_args
    if live: args+=['-cdrom',str(iso),'-kernel',str(root/'vmlinuz'),'-initrd',str(root/'initrd'),'-append','boot=casper console=tty0 console=ttyS0,115200 ---']
    else: args+=['-boot','c']
    (root/(stage+'-command.json')).write_text(json.dumps(args,indent=2))
    p=subprocess.Popen(args,stdout=subprocess.DEVNULL,stderr=(root/(stage+'-qemu.log')).open('w'))
    s=None; text=''; seen=set(); success='INSTALL_PASS' if live else 'DISK_BOOT_PASS'
    deadline=time.monotonic()+(2400 if live else 7200)
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
        boot_start=time.monotonic();next_frame=0;frame_times=(3,5,8,12,16,20,25,30,35,40,50,60)
        while time.monotonic()<deadline:
            if stage=='updated-reboot' and next_frame<len(frame_times) and time.monotonic()-boot_start>=frame_times[next_frame]:
                ppm=root/(stage+'-boot-'+str(frame_times[next_frame])+'.ppm')
                response=command({'execute':'screendump','arguments':{'filename':str(ppm)}})
                if 'error' not in response:Image.open(ppm).save(ppm.with_suffix('.png'));ppm.unlink()
                next_frame+=1
            console=serial.read_text(errors='replace') if serial.exists() else ''
            text=evidence.read_text(errors='replace') if evidence.exists() else ''
            if 'gitm-installer-probe.service: Failed with result' in console:
                raise RuntimeError('Guest test helper failed; inspect serial log')
            for label in re.findall(r'GITM_INSTALL_TEST\|FRAME\|([a-z-]+)',text):
                if label in seen: continue
                seen.add(label); ppm=root/(stage+'-'+label+'.ppm')
                r=command({'execute':'screendump','arguments':{'filename':str(ppm)}})
                if 'error' in r: raise RuntimeError(r)
                Image.open(ppm).save(ppm.with_suffix('.png')); ppm.unlink()
                print('INSTALL_FRAME|'+stage+'|'+label,flush=True)
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
boot('updated-reboot',False)
(root/'result.json').write_text(json.dumps({'install':'pass','disk_boot':'pass','boot_mode':'UEFI' if options.uefi else 'BIOS','disk_bytes':40*1024**3,'live_media_removed':True},indent=2))
print('PASS: installation completed and native Plasma booted with / on the installed vda partition')

