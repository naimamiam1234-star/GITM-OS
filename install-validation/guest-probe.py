#!/usr/bin/python3
"""Test-only startup probe. Never navigates or submits the installer wizard."""
import base64, glob, json, os, pathlib, pwd, shutil, subprocess, tarfile, time
out = pathlib.Path('/run/gitm-installer-evidence'); out.mkdir(exist_ok=True)
serial = open('/dev/ttyS0', 'w', buffering=1)
def mark(s): serial.write('GITM_INSTALL_PROBE|' + s + '\n')
def capture(name, args, timeout=30, env=None):
    try:
        r = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout, env=env)
        (out/name).write_bytes(r.stdout); mark(name + '|exit=' + str(r.returncode)); return r.returncode
    except Exception as e: (out/name).write_text(repr(e)); mark(name+'|error='+repr(e))
capture('packages.txt', ['dpkg-query','-W','calamares','pkexec','polkitd','qt6-base-dev'])
capture('disks.txt', ['lsblk','-o','NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS,MODEL'])
capture('mounts.txt', ['findmnt'])
capture('launcher.txt', ['cat','/usr/local/bin/gitm-install'])
for p in ['/etc/calamares','/usr/share/calamares','/usr/share/polkit-1/actions']:
    if not os.path.exists(p): continue
    files=[]
    for source in pathlib.Path(p).rglob('*'):
        if not source.is_file(): continue
        files.append(str(source))
        # Preserve configuration, not large module binaries or branding images:
        # the archive is transported over the guest serial console.
        if source.suffix not in ['.conf','.yaml','.yml','.desc','.desktop','.policy'] and source.name != 'settings.conf': continue
        target=out/pathlib.Path(p).name/source.relative_to(p)
        target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(source,target)
    (out/(pathlib.Path(p).name+'-files.txt')).write_text('\n'.join(files))
env = None; uid = None
for attempt in range(600):
    for item in glob.glob('/proc/[0-9]*/comm'):
        try:
            if pathlib.Path(item).read_text().strip() != 'plasmashell': continue
            proc = pathlib.Path(item).parent; uid=proc.stat().st_uid
            if uid == 0: continue
            env = dict(x.decode(errors='replace').split('=',1) for x in (proc/'environ').read_bytes().split(b'\0') if b'=' in x)
            if env.get('DISPLAY'): break
        except (OSError, ValueError): continue
    if env and env.get('DISPLAY'): break
    time.sleep(1)
try:
    if not env or not env.get('DISPLAY'): raise RuntimeError('No X11 Plasma session found')
    user=pwd.getpwuid(uid); time.sleep(30)
    (out/'session-environment.json').write_text(json.dumps({k:env.get(k) for k in ['DISPLAY','XAUTHORITY','XDG_SESSION_TYPE','XDG_RUNTIME_DIR','QT_STYLE_OVERRIDE','QT_QPA_PLATFORMTHEME']},indent=2))
    capture('help.txt', ['/usr/bin/calamares','--help'], env=env)
    capture('version.txt', ['/usr/bin/calamares','--version'], env=env)
    def launch(label, argv, launchenv, as_user=False):
        mark(label+'|starting')
        def demote(): os.initgroups(user.pw_name,user.pw_gid); os.setgid(user.pw_gid); os.setuid(uid)
        with (out/(label+'.txt')).open('wb') as log:
            p=subprocess.Popen(argv,env=launchenv,stdout=log,stderr=subprocess.STDOUT,preexec_fn=demote if as_user else None)
            time.sleep(40); mark('FRAME|'+label); time.sleep(10)
            if p.poll() is None:
                mark(label+'|alive-at-50s'); p.terminate()
                try: p.wait(timeout=5)
                except subprocess.TimeoutExpired: p.kill(); p.wait()
                mark(label+'|terminated-by-probe='+str(p.returncode))
            else: mark(label+'|actual-exit='+str(p.returncode))
        subprocess.run(['pkill','-TERM','-x','calamares'],check=False); time.sleep(5)
        for path in ['/root/.cache/calamares',user.pw_dir+'/.cache/calamares','/var/log/Calamares.log']:
            if os.path.isdir(path): shutil.copytree(path,out/(label+'-'+path.replace('/','_')),dirs_exist_ok=True)
            elif os.path.isfile(path): shutil.copy2(path,out/(label+'-'+path.replace('/','_')))
    launch('normal-launcher',['/usr/local/bin/gitm-install'],env,True)
    rootenv=env.copy(); rootenv.update(HOME='/root',USER='root',LOGNAME='root')
    launch('root-debug',['/usr/bin/calamares','--debug'],rootenv)
except Exception as e: mark('ERROR|'+repr(e)); (out/'probe-error.txt').write_text(repr(e))
capture('journal.txt',['journalctl','-b','--no-pager','-n','1500'])
capture('processes.txt',['ps','auxww'])
archive='/run/gitm-installer-evidence.tar.gz'
with tarfile.open(archive,'w:gz') as tar: tar.add(out,arcname='guest')
payload=base64.b64encode(pathlib.Path(archive).read_bytes()).decode()
mark('ARCHIVE_BEGIN')
for i in range(0,len(payload),3072): mark('DATA|'+payload[i:i+3072])
mark('ARCHIVE_END'); mark('DONE')
