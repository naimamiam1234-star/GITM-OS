#!/usr/bin/python3
"""Destructive only to the single serial-tagged disposable CI disk; never ship in ISO."""
import base64, fcntl, glob, json, os, pathlib, re, subprocess, tarfile, time
P = pathlib.Path
out=P('/run/gitm-install-evidence'); out.mkdir(exist_ok=True)
lock=open('/run/gitm-install-test.lock','w')
try: fcntl.flock(lock,fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError: raise SystemExit(0)
serial=open('/dev/ttyS0','w',buffering=1)
def mark(s): serial.write('GITM_INSTALL_TEST|'+s+'\n')
def run(args, env=None, check=True):
    return subprocess.run(args,env=env,check=check,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True).stdout

def session(timeout=600):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        for c in glob.glob('/proc/[0-9]*/comm'):
            try:
                p=P(c).parent
                if P(c).read_text().strip()!='plasmashell' or p.stat().st_uid==0: continue
                e=dict(x.decode().split('=',1) for x in (p/'environ').read_bytes().split(b'\0') if b'=' in x)
                if e.get('DISPLAY'): return e
            except (OSError,ValueError,UnicodeError): pass
        time.sleep(1)
    raise RuntimeError('Native Plasma X11 session did not appear')

def archive():
    (out/'journal.txt').write_text(run(['journalctl','-b','--no-pager','-n','3000'],check=False))
    (out/'lsblk.json').write_text(run(['lsblk','-J','-b','-o','NAME,PATH,TYPE,SIZE,SERIAL,FSTYPE,MOUNTPOINTS']))
    for src in ['/var/log/Calamares.log','/root/.cache/calamares/session.log','/tmp/calamares.log']:
        if P(src).is_file(): (out/P(src).name).write_bytes(P(src).read_bytes())
    tar=P('/run/install-evidence.tar.gz')
    with tarfile.open(tar,'w:gz') as t: t.add(out,arcname='guest')
    data=base64.b64encode(tar.read_bytes()).decode(); mark('ARCHIVE_BEGIN')
    for n in range(0,len(data),3072): mark('DATA|'+data[n:n+3072])
    mark('ARCHIVE_END')

def main():
    if 'boot=casper' not in P('/proc/cmdline').read_text():
        source=run(['findmnt','-n','-o','SOURCE','/']).strip()
        if not re.fullmatch(r'/dev/vda[1-9][0-9]*(?:\[.*\])?',source): raise RuntimeError('Installed root is not a vda partition: '+source)
        env=session(); time.sleep(20)
        (out/'installed-root.txt').write_text(run(['findmnt','/']))
        (out/'installed-packages.txt').write_text(run(['dpkg-query','-W','plasma-desktop','plasma-workspace','calamares']))
        mark('FRAME|installed-desktop'); time.sleep(8); archive(); mark('DISK_BOOT_PASS'); return
    devices=json.loads(run(['lsblk','-J','-b','-o','NAME,PATH,TYPE,SIZE,SERIAL']))['blockdevices']
    disks=[d for d in devices if d['type']=='disk']
    if len(disks)!=1 or disks[0]['path']!='/dev/vda' or disks[0]['size']!=40*1024**3 or disks[0].get('serial')!='GITM-CI-ONLY' or disks[0].get('children'):
        raise RuntimeError('Fixture disk identity or blankness mismatch: '+repr(disks))
    # Test-only last job executes only after all normal installation jobs succeed.
    config=CONFIG.copy()
    settings=config.get('settings.conf','')
    before='bootloader, umount]'
    if settings.count(before)!=1: raise RuntimeError('Cannot locate final umount job for completion sentinel')
    settings=settings.replace(before,'bootloader, umount, shellprocess@gitm-ci-pass]')
    settings+='\n - id: gitm-ci-pass\n   module: shellprocess\n   config: gitm-ci-pass.conf\n'
    config['settings.conf']=settings
    config['modules/gitm-ci-pass.conf']='dontChroot: true\ntimeout: 30\nscript:\n - \"touch /run/gitm-install-jobs-complete\"\n'
    # These texts are embedded by prepare.sh from the checked-out candidate.
    for name,text in config.items():
        dest=P('/etc/calamares')/name; dest.parent.mkdir(parents=True,exist_ok=True); dest.write_text(text)
        evidence=out/'config'/name; evidence.parent.mkdir(parents=True,exist_ok=True); evidence.write_text(text)
    env=session(); time.sleep(25); env.update(HOME='/root',USER='root',LOGNAME='root')
    run(['xrandr','--output','Virtual-1','--mode','1280x800'],env,check=False)
    log=(out/'calamares-debug.log').open('w')
    proc=subprocess.Popen(['/usr/bin/calamares','--debug'],env=env,stdout=log,stderr=subprocess.STDOUT)
    def x(*args): return run(['xdotool',*map(str,args)],env)
    win=None
    for _ in range(90):
        ids=run(['xdotool','search','--onlyvisible','--class','calamares'],env,check=False).split()
        if ids: win=ids[-1]; break
        if proc.poll() is not None: raise RuntimeError('Calamares exited at startup')
        time.sleep(1)
    if not win: raise RuntimeError('Calamares window missing')
    x('windowsize',win,1024,520); x('windowmove',win,128,153)
    def frame(label):
        # Force a compositor repaint before the host captures the page.
        x('windowminimize',win); time.sleep(.5); x('windowmap',win); x('windowactivate','--sync',win)
        time.sleep(2); mark('FRAME|'+label); time.sleep(8)
    def click(a,b): x('mousemove','--sync',a,b); x('click',1); time.sleep(3)
    frame('welcome')
    click(1000,650); frame('location')
    click(1000,650); frame('keyboard')
    click(1000,650); frame('partitions')
    click(334,227); frame('erase-preview')
    click(1000,650); frame('users')
    for a,b,value in [(425,205,'GITM CI'),(425,273,'gitmtest'),(425,341,'gitm-ci'),(425,409,'GITMciTest42'),(625,409,'GITMciTest42')]:
        click(a,b); x('key','ctrl+a'); x('type','--clearmodifiers',value)
    click(334,448); click(1000,650); frame('summary')
    logs=(out/'calamares-debug.log').read_text(errors='replace')
    (out/'pre-confirm-plan.log').write_text(logs)
    # Fail closed: a mere disk/free-space preview is not a root plan.
    partition=re.search(r'/dev/vda[1-9][0-9]*',logs)
    root_mapping=re.search(r'(?:mount.?point|mounting|mountPoint)[^\n]{0,100}(?:[\"\s:]\/([\"\s,;]|$))',logs,re.I)
    if not partition or not root_mapping: raise RuntimeError('No explicit vda partition and / mapping in pre-confirm log; refusing installation')
    mark('PLAN_GUARD_PASS|'+partition.group())
    click(1000,733); frame('confirmation'); click(744,458); mark('INSTALL_CONFIRMED')
    injected=False; end=time.monotonic()+1500
    while time.monotonic()<end:
        mounts=json.loads(run(['findmnt','-J','-o','SOURCE,TARGET']))['filesystems']
        def flatten(items):
            for d in items:
                yield d
                yield from flatten(d.get('children',[]))
        for m in flatten(mounts):
            if not re.fullmatch(r'/dev/vda[1-9][0-9]*',m['source']): continue
            root=P(m['target'])
            if root==P('/') or not (root/'etc/os-release').exists() or not (root/'usr/bin/python3').exists(): continue
            # Calamares rsync creates these first; install isolated filenames only.
            lib=root/'usr/local/lib/gitm-probe'; lib.mkdir(parents=True,exist_ok=True)
            (lib/'guest-probe.py').write_bytes(P(__file__).read_bytes())
            units=root/'etc/systemd/system'; units.mkdir(parents=True,exist_ok=True)
            (units/'gitm-installed-verifier.service').write_text('[Unit]\nAfter=display-manager.service\n[Service]\nType=simple\nExecStart=/usr/bin/python3 /usr/local/lib/gitm-probe/guest-probe.py\n[Install]\nWantedBy=multi-user.target\n')
            wants=units/'multi-user.target.wants'; wants.mkdir(exist_ok=True)
            link=wants/'gitm-installed-verifier.service'
            if not link.exists(): link.symlink_to('../gitm-installed-verifier.service')
            if not injected: mark('TARGET_ROOT_PROOF|'+m['source']+'|'+str(root)); injected=True
        logs=(out/'calamares-debug.log').read_text(errors='replace')
        if P('/run/gitm-install-jobs-complete').is_file():
            if not injected: raise RuntimeError('Installation finished without target-root proof')
            frame('installation-complete'); archive(); mark('INSTALL_PASS'); return
        if proc.poll() is not None: raise RuntimeError('Installer exited before proven completion')
        time.sleep(2)
    raise RuntimeError('Installation timed out')

CONFIG = {} # replaced by prepare.sh in the test-only helper copy
try: main()
except Exception as e:
    mark('ERROR|'+repr(e))
    (out/'error.txt').write_text(repr(e)); archive()
