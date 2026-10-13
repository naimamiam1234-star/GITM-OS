"""Add the actual candidate .deb to disposable installation/update fixtures only."""
import ast,gzip,hashlib,importlib.util,pathlib,subprocess,sys
root=pathlib.Path(__file__).resolve().parents[1];iso=sys.argv[1];package=pathlib.Path(sys.argv[2]);digest=hashlib.sha256(package.read_bytes()).hexdigest()
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
            transaction('install-app-package',['apt-get','install','-y',str(candidate)])
            if sentinel.read_text()!='Synthetic CI fixture, not customer data':raise RuntimeError('User sentinel modified')
            if run(['dpkg-query','-W','-f=${Version}','gitm-autodiag']).strip()!='3.3.1-1':raise RuntimeError('Candidate version not installed')
""".replace('EXPECTED_CANDIDATE',repr(digest))
code=code[:start]+replacement+code[end:]
anchor="            lib=root/'usr/local/lib/gitm-probe'; lib.mkdir(parents=True,exist_ok=True)"
copy="""            candidate=root/'var/lib/gitm-app-candidate.deb'
            if not candidate.exists():candidate.parent.mkdir(parents=True,exist_ok=True);candidate.write_bytes(P('/var/lib/gitm-app-candidate.deb').read_bytes())
"""
assert code.count(anchor)==1;code=code.replace(anchor,copy+anchor)
anchor="        mark('UPDATE_REBOOT_VERIFIED')"
proof="""        user=pwd.getpwnam('gitmtest');sentinel=P(user.pw_dir)/'.local/share/gitm/update-preservation-sentinel.txt'
        if sentinel.read_text()!='Synthetic CI fixture, not customer data':raise RuntimeError('Sentinel missing after reboot')
        (out/'user-data-preservation.txt').write_text('Synthetic sentinel retained; no production workshop data tested')
        key=P('/usr/share/gitm/update-public.pem')
        after=__import__('hashlib').sha256(key.read_bytes()).hexdigest()
        if after!=(state/'signing-key-before.txt').read_text():raise RuntimeError('Signing key changed after reboot')
        (out/'signing-key-sha256.txt').write_text(after)
"""
assert code.count(anchor)==1;code=code.replace(anchor,proof+anchor);ast.parse(code);helper.write_text(code)
spec=importlib.util.spec_from_file_location('inject',root/'install-validation/inject-initrd.py');inject=importlib.util.module_from_spec(spec);spec.loader.exec_module(inject)
hook=inject.HOOK.replace(b'cp /gitm-probe/guest-probe.py',b'cp /gitm-probe/candidate.deb "$target/var/lib/gitm-app-candidate.deb"\ncp /gitm-probe/guest-probe.py')
assert b'candidate.deb' in hook
subprocess.run([sys.executable,str(root/'install-validation/inject-initrd.py'),str(out/'initrd.original'),str(out/'initrd'),'--helper',str(helper)],check=True)
extra=inject.cpio([('gitm-probe/candidate.deb',0o100644,package.read_bytes()),('scripts/casper-bottom/99gitm-installer-probe',0o100755,hook)])
with (out/'initrd').open('ab') as stream:stream.write(gzip.compress(extra,mtime=0))
print('PASS: ephemeral candidate prepared; ISO unchanged',digest)
