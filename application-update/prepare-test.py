"""Add the actual candidate .deb to disposable installation/update fixtures only."""
import ast,gzip,hashlib,importlib.util,pathlib,subprocess,sys
root=pathlib.Path(__file__).resolve().parents[1];iso=sys.argv[1];package=pathlib.Path(sys.argv[2]);digest=hashlib.sha256(package.read_bytes()).hexdigest()
resource_packages=[pathlib.Path(x) for x in sys.argv[3:]]
resource_digests={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in resource_packages}
subprocess.run([sys.executable,str(root/'update-validation/prepare.py'),iso],check=True)
out=pathlib.Path('dist/disk-install');helper=out/'guest-install-embedded.py';code=helper.read_text()
start=code.index("            package=P('/tmp/gitm-app-package')")
end=code.index("            if hashlib.sha256(key.read_bytes()).hexdigest()!=before",start)
replacement="""            import hashlib
            key=P('/usr/share/gitm/update-public.pem'); before=hashlib.sha256(key.read_bytes()).hexdigest()
            (state/'signing-key-before.txt').write_text(before)
            candidate=P('/var/lib/gitm-app-candidate.deb')
            if hashlib.sha256(candidate.read_bytes()).hexdigest()!=EXPECTED_CANDIDATE:raise RuntimeError('Candidate package hash mismatch')
            user=pwd.getpwnam('gitmtest');sentinel=P(user.pw_dir)/'.local/share/gitm/update-preservation-sentinel.txt';sentinel.parent.mkdir(parents=True,exist_ok=True);os.chown(sentinel.parent,user.pw_uid,user.pw_gid);sentinel.write_text('Synthetic CI fixture, not customer data');os.chown(sentinel,user.pw_uid,user.pw_gid)
            resources=[]
            for name,digest in RESOURCE_DIGESTS.items():
                file=P('/var/lib')/name
                if hashlib.sha256(file.read_bytes()).hexdigest()!=digest:raise RuntimeError('Resource package hash mismatch')
                resources.append(str(file))
            splash=P('/etc/xdg/ksplashrc')
            owner=subprocess.run(['dpkg-query','-S',str(splash)],capture_output=True,text=True)
            (out/'ksplash-before.txt').write_text(owner.stdout+owner.stderr+(splash.read_text() if splash.is_file() else 'No prior global splash configuration'))
            transaction('install-app-package',['apt-get','install','-y',str(candidate)]+resources)
            if sentinel.read_text()!='Synthetic CI fixture, not customer data':raise RuntimeError('User sentinel modified')
            if run(['dpkg-query','-W','-f=${Version}','gitm-autodiag']).strip()!='3.5.0~preview1':raise RuntimeError('Candidate version not installed')
            shortcut=P('/usr/share/applications/gitm-assistant.desktop')
            if not shortcut.is_file() or '--assistant' not in shortcut.read_text():raise RuntimeError('Assistant launcher missing')
""".replace('EXPECTED_CANDIDATE',repr(digest)).replace('RESOURCE_DIGESTS',repr(resource_digests))
copy_resources=''.join("            file=root/'var/lib'/"+repr(p.name)+";file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes((P('/var/lib')/"+repr(p.name)+").read_bytes())\n" for p in resource_packages)
code=code[:start]+replacement+code[end:]
anchor="            lib=root/'usr/local/lib/gitm-probe'; lib.mkdir(parents=True,exist_ok=True)"
copy="""            candidate=root/'var/lib/gitm-app-candidate.deb'
            if not candidate.exists():candidate.parent.mkdir(parents=True,exist_ok=True);candidate.write_bytes(P('/var/lib/gitm-app-candidate.deb').read_bytes())
"""
assert code.count(anchor)==1;code=code.replace(anchor,copy+copy_resources+anchor)
anchor="        mark('UPDATE_REBOOT_VERIFIED')"
proof="""        user=pwd.getpwnam('gitmtest');sentinel=P(user.pw_dir)/'.local/share/gitm/update-preservation-sentinel.txt'
        if sentinel.read_text()!='Synthetic CI fixture, not customer data':raise RuntimeError('Sentinel missing after reboot')
        (out/'user-data-preservation.txt').write_text('Synthetic sentinel retained; no production workshop data tested')
        key=P('/usr/share/gitm/update-public.pem')
        after=__import__('hashlib').sha256(key.read_bytes()).hexdigest()
        if after!=(state/'signing-key-before.txt').read_text():raise RuntimeError('Signing key changed after reboot')
        (out/'signing-key-sha256.txt').write_text(after)
        for pkg in ('gitm-autodiag','gitm-sdk-sources','gitm-obdb-data'):
            if run(['dpkg','--verify',pkg]).strip():raise RuntimeError('Installed package integrity mismatch: '+pkg)
        theme=P('/usr/share/plymouth/themes/default.plymouth').resolve()
        if str(theme)!='/usr/share/plymouth/themes/gitm/gitm.plymouth':raise RuntimeError('Branding theme not selected')
        if not P('/usr/share/plymouth/themes/gitm/watermark.png').is_file():raise RuntimeError('Boot logo missing')
        config=theme.read_text()
        if 'ImageDir=/usr/share/plymouth/themes/gitm' not in config.splitlines():raise RuntimeError('Boot images still point at native Ubuntu theme')
        (out/'plymouth-theme.txt').write_text(config)
        native=P(user.pw_dir)/'.config/plasma-org.kde.plasma.desktop-appletsrc'
        if native.is_file():(out/'plasma-wallpaper-config.txt').write_text(native.read_text())
        (out/'boot-branding-selected.txt').write_text(str(theme))
"""
assert code.count(anchor)==1;code=code.replace(anchor,proof+anchor);ast.parse(code);helper.write_text(code)
anchor='            except subprocess.TimeoutExpired: app.kill(); app.wait()\n'
bench="""            bench=P(user.pw_dir)/'.local/share/gitm/assistant-bench-3.4.0'
            result=subprocess.run(['/opt/gitm-venv/bin/python','/opt/gitm/assistant-bench.py',str(bench)],env={**env,'GITM_BENCH_WIDTH':'1280','GITM_BENCH_HEIGHT':'800'},stdout=log,stderr=subprocess.STDOUT,preexec_fn=demote,timeout=90)
            if result.returncode:raise RuntimeError('Installed assistant simulator bench failed')
            for artifact in bench.iterdir():
                if artifact.suffix in ('.png','.json'): (out/('assistant-'+artifact.name)).write_bytes(artifact.read_bytes())
            brand=P(user.pw_dir)/'.local/share/gitm/branding-bench-3.4.0'
            result=subprocess.run(['/opt/gitm-venv/bin/python','/opt/gitm/branding-bench.py',str(brand)],env=env,stdout=log,stderr=subprocess.STDOUT,preexec_fn=demote,timeout=90)
            if result.returncode:raise RuntimeError('Installed branding bench failed')
            for artifact in brand.iterdir():
                if artifact.suffix in ('.png','.json'): (out/('branding-'+artifact.name)).write_bytes(artifact.read_bytes())
            proof=__import__('json').loads((bench/'proof.json').read_text())
            if not proof['reading_continues_with_panel'] or proof['sample_count']<4:raise RuntimeError('Assistant interrupted live acquisition')
"""
assert code.count(anchor)==1;code=code.replace(anchor,anchor+bench);ast.parse(code);helper.write_text(code)
spec=importlib.util.spec_from_file_location('inject',root/'install-validation/inject-initrd.py');inject=importlib.util.module_from_spec(spec);spec.loader.exec_module(inject)
hook=inject.HOOK.replace(b'cp /gitm-probe/guest-probe.py',b'cp /gitm-probe/candidate.deb "$target/var/lib/gitm-app-candidate.deb"\ncp /gitm-probe/guest-probe.py')
assert b'candidate.deb' in hook
subprocess.run([sys.executable,str(root/'install-validation/inject-initrd.py'),str(out/'initrd.original'),str(out/'initrd'),'--helper',str(helper)],check=True)
entries=[('gitm-probe/candidate.deb',0o100644,package.read_bytes()),('scripts/casper-bottom/99gitm-installer-probe',0o100755,hook)]
for p in resource_packages:
 entries.append(('gitm-probe/'+p.name,0o100644,p.read_bytes()))
 hook=hook.replace(b'cp /gitm-probe/guest-probe.py',('cp /gitm-probe/'+p.name+' \"$target/var/lib/'+p.name+'\"\n').encode()+b'cp /gitm-probe/guest-probe.py')
entries[1]=('scripts/casper-bottom/99gitm-installer-probe',0o100755,hook)
extra=inject.cpio(entries)
with (out/'initrd').open('ab') as stream:stream.write(gzip.compress(extra,mtime=0))
print('PASS: ephemeral candidate prepared; ISO unchanged',digest)

