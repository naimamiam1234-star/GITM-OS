import pathlib, subprocess, sys
root=pathlib.Path(__file__).resolve().parents[1]
p=root/'install-validation/guest-install.py'
s=p.read_text();marker='        env=session(); time.sleep(20)'
insert='''        state=P('/var/lib/gitm-update-test'); state.mkdir(exist_ok=True)
        if not (state/'completed').exists():
            def transaction(name,argv):
                with (state/(name+'.log')).open('w') as log:
                    result=subprocess.run(argv,stdout=log,stderr=subprocess.STDOUT,timeout=3600,env={**os.environ,'DEBIAN_FRONTEND':'noninteractive'})
                if result.returncode:raise RuntimeError(name+' failed: '+(state/(name+'.log')).read_text()[-1000:])
            transaction('packages-before',['dpkg-query','-W'])
            transaction('apt-refresh',['apt-get','update'])
            transaction('apt-plan',['apt-get','-s','upgrade'])
            transaction('apt-upgrade',['apt-get','-y','-o','Dpkg::Options::=--force-confold','upgrade'])
            package=P('/tmp/gitm-app-package'); (package/'DEBIAN').mkdir(parents=True,exist_ok=True)
            import shutil, hashlib
            key=P('/usr/share/gitm/update-public.pem'); before=hashlib.sha256(key.read_bytes()).hexdigest()
            shutil.copytree('/opt/gitm',package/'opt/gitm',dirs_exist_ok=True)
            (package/'DEBIAN/control').write_text('Package: gitm-autodiag\\nVersion: 3.3.0+updateprobe1\\nArchitecture: all\\nMaintainer: GITM Project\\nDescription: Same application packaged for update transaction validation\\n')
            transaction('build-app-package',['dpkg-deb','--root-owner-group','--build',str(package),'/tmp/gitm-app-update.deb'])
            transaction('install-app-package',['apt-get','install','-y','/tmp/gitm-app-update.deb'])
            if hashlib.sha256(key.read_bytes()).hexdigest()!=before:raise RuntimeError('Signing trust changed')
            transaction('packages-after',['dpkg-query','-W'])
            (state/'completed').write_text('APT transaction and application package installed; awaiting reboot')
            os.sync(); archive(); mark('DISK_BOOT_PASS'); return
        transaction_log=state/'packages-after.log'
        if not transaction_log.exists():raise RuntimeError('Previous update evidence missing')
        import shutil
        shutil.copytree(state,out/'update-transaction',dirs_exist_ok=True)
        (out/'updated-app-version.txt').write_text(run(['dpkg-query','-W','gitm-autodiag']))
        (out/'updated-app-integrity.txt').write_text(run(['dpkg','--verify','gitm-autodiag']))
        mark('UPDATE_REBOOT_VERIFIED')
'''
assert s.count(marker)==1;p.write_text(s.replace(marker,insert+marker))
subprocess.run(['bash',str(root/'install-validation/prepare.sh'),sys.argv[1],'dist/disk-install','disk'],check=True)
