#!/usr/bin/env python3
"""Extract the shipped gallery driver and override only fixture cleanup in initrd."""
import argparse,gzip,hashlib,importlib.util,json,pathlib,stat,subprocess
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('iso',type=pathlib.Path);p.add_argument('initrd',type=pathlib.Path);p.add_argument('output',type=pathlib.Path)
a=p.parse_args(); work=a.output.parent/'gallery-driver-fixture'; work.mkdir(parents=True,exist_ok=True)
squash=work/'filesystem.squashfs'
subprocess.run(['xorriso','-osirrox','on','-indev',str(a.iso),'-extract','/casper/filesystem.squashfs',str(squash)],check=True)
source=subprocess.run(['unsquashfs','-cat',str(squash),'opt/gitm/gallery_runner.py'],check=True,stdout=subprocess.PIPE).stdout.decode()
(work/'shipped-gallery_runner.py').write_text(source)
helpers='''
import time
def fixture_installer(line):
 fields=line.split(None,4)
 if len(fields)<5:return False
 try:comm=Path('/proc/'+fields[2]+'/comm').read_text().strip()
 except OSError:comm=''
 return comm=='calamares' or 'GITM OS Installer' in fields[4] or 'Cancel Installation' in fields[4]
def fixture_minimize_installer():
 for line in windows():
  if not fixture_installer(line):continue
  wid=line.split()[0]
  result=subprocess.run(['xdotool','windowminimize',wid],capture_output=True,text=True)
  if result.returncode:raise RuntimeError('Fixture could not minimize installer '+wid)
  emit('GITM_GALLERY_INSTALLER_MINIMIZED|'+wid)
 deadline=time.monotonic()+2
 while not fixture_verify_hidden(report=False):
  if time.monotonic()>=deadline:fixture_verify_hidden()
  time.sleep(0.05)
 fixture_verify_hidden()
def fixture_verify_hidden(report=True):
 result=subprocess.run(['xdotool','search','--onlyvisible','--name','.*'],capture_output=True,text=True)
 visible={int(x) for x in result.stdout.split() if x.isdigit()}
 for line in windows():
  if fixture_installer(line) and int(line.split()[0],16) in visible:
   if not report:return False
   emit('GITM_GALLERY_ERROR|fixture-cleanup|Installer remains visible')
   raise RuntimeError('Fixture installer still visible before later capture')
 if report:emit('GITM_GALLERY_INSTALLER_HIDDEN|PASS')
 return True
def fixture_installer_process(key,process):
 return key=='install' or Path(process.program()).name in {'calamares','gitm-install'}
'''
anchor='class Gallery(QObject):'
if source.count(anchor)!=1:raise RuntimeError('Unsupported shipped Gallery class')
patched=source.replace(anchor,helpers+'\n'+anchor)
anchor='  for line in windows():\n   subprocess.run([\'wmctrl\',\'-ic\',line.split()[0]],check=False)'
if patched.count(anchor)!=1:raise RuntimeError('Unsupported shipped wmctrl cleanup')
patched=patched.replace(anchor,"  fixture_minimize_installer()\n  for line in windows():\n   if fixture_installer(line):continue\n   subprocess.run(['wmctrl','-ic',line.split()[0]],check=False)")
anchor='  for process in self.w.processes.values():\n'
if patched.count(anchor)!=1:raise RuntimeError('Unsupported shipped process cleanup')
patched=patched.replace(anchor,'  for key,process in self.w.processes.items():\n   if fixture_installer_process(key,process):continue\n')
anchor=' def capture(self,name):\n'
if patched.count(anchor)!=1:raise RuntimeError('Unsupported shipped capture method')
patched=patched.replace(anchor,anchor+"  if name!='app-install':fixture_verify_hidden()\n")
compile(patched,'fixture-gallery_runner.py','exec'); (work/'fixture-gallery_runner.py').write_text(patched)
# Reuse the independently checked parser/encoder, but install a gallery-only hook.
spec=importlib.util.spec_from_file_location('initrd_tools',pathlib.Path(__file__).resolve().parents[1]/'install-validation/inject-initrd.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
original=a.initrd.read_bytes(); selected,members=m.inspect(original);order=selected.get('scripts/casper-bottom/ORDER')
if not order:raise RuntimeError('Missing original casper-bottom ORDER')
hookname='scripts/casper-bottom/99gitm-gallery-fixture'
if hookname.encode() in order:raise RuntimeError('Gallery fixture hook already present')
updated=order.rstrip(b'\n')+b'\n/'+hookname.encode()+b' "$@"\n[ -e /conf/param.conf ] && . /conf/param.conf\n'
hook=b'''#!/bin/sh
case "$1" in prereqs) exit 0;; esac
target=${rootmnt:-/root}
test -f "$target/opt/gitm/gallery_runner.py" || exit 1
cp /gitm-gallery-fixture/gallery_runner.py "$target/opt/gitm/gallery_runner.py"
echo 'GITM_GALLERY_FIXTURE_OVERRIDE|installed' >/dev/ttyS0
'''
files=[(x,stat.S_IFDIR|0o755,b'') for x in ['scripts','scripts/casper-bottom','gitm-gallery-fixture']]
files += [('scripts/casper-bottom/ORDER',stat.S_IFREG|0o644,updated),(hookname,stat.S_IFREG|0o755,hook),('gitm-gallery-fixture/gallery_runner.py',stat.S_IFREG|0o644,patched.encode())]
a.output.write_bytes(original+gzip.compress(m.cpio(files),mtime=0))
roundtrip,_=m.inspect(a.output.read_bytes())
if roundtrip['scripts/casper-bottom/ORDER']!=updated:raise RuntimeError('Hook ORDER roundtrip failed')
with a.iso.open('rb') as iso_file: iso_sha256=hashlib.file_digest(iso_file,'sha256').hexdigest()
report={'iso_sha256':iso_sha256,'shipped_driver_sha256':hashlib.sha256(source.encode()).hexdigest(),'fixture_driver_sha256':hashlib.sha256(patched.encode()).hexdigest(),'scope':'test-only installer minimize and visibility guard','original_initrd_members':members}
(work/'fixture-report.json').write_text(json.dumps(report,indent=2));squash.unlink()
print(json.dumps(report,indent=2))
