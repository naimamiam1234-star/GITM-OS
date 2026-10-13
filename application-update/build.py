"""Build an application-only .deb from the verified existing GITM ISO."""
import argparse,hashlib,json,pathlib,shutil,subprocess,tempfile
EXPECTED_BASE_DEB='e80e19fa6bdcca214dda03d027d5c07c1c32ecb4110c6fcc22cf8ca2f3cd877f'
EXPECTED='d5e7851cac398f2ed2aad2fe62e72913bfb5b0950fa048273b2aaa7d6a8e56be'
ROOT=pathlib.Path(__file__).resolve().parents[1]
def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def run(*argv):subprocess.run([str(a) for a in argv],check=True)
def main():
 p=argparse.ArgumentParser();p.add_argument('iso',type=pathlib.Path);p.add_argument('--output',type=pathlib.Path,default=pathlib.Path('dist/app-update'));a=p.parse_args()
 base_deb=a.iso.suffix=='.deb'
 if sha(a.iso)!=(EXPECTED_BASE_DEB if base_deb else EXPECTED):raise ValueError('Existing base input SHA256 mismatch')
 a.output.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory(prefix='gitm-app-build-') as tmp:
  tmp=pathlib.Path(tmp);sq=tmp/'filesystem.squashfs';stage=tmp/'package'
  if base_deb:run('dpkg-deb','--extract',a.iso,stage)
  else:
   run('xorriso','-osirrox','on','-indev',a.iso,'-extract','/casper/filesystem.squashfs',sq)
   run('unsquashfs','-no-progress','-d',stage,sq,'opt/gitm')
  app=stage/'opt/gitm'
  if not (app/'native.py').exists():raise ValueError('Existing GITM application missing')
  run('python3',ROOT/'diag-integration/install.py',app)
  for cache in list(app.rglob('__pycache__')):shutil.rmtree(cache)
  (app/'gitm-app-release.json').write_text(json.dumps({'version':'3.4.0','debian_version':'3.4.0-2','source_iso_sha256':EXPECTED,'delivery':'local administrative Debian package; not a signed gitmupdate'},indent=2))
  shutil.copytree(ROOT/'diag-integration/system-integration',stage,dirs_exist_ok=True)
  watermark=stage/'usr/share/plymouth/themes/gitm/watermark.png';watermark.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(app/'assets/branding/symbol.png',watermark)
  control=stage/'DEBIAN';control.mkdir()
  (control/'control').write_text('Package: gitm-autodiag\nVersion: 3.4.0-2\nArchitecture: all\nMaintainer: GITM OS Project\nDepends: python3, plymouth, plymouth-theme-spinner\nDescription: Application-only GITM AutoDiag update for existing GITM OS\n Includes sourced brand assets and model names, retains installed runtime and user data.\n')
  (control/'conffiles').write_text('/etc/default/grub.d/91-gitm-branding.cfg\n/etc/xdg/ksplashrc\n')
  pre=control/'preinst';pre.write_text('#!/bin/sh\nset -eu\n[ "$(dpkg --print-architecture)" = amd64 ]\n[ -x /opt/gitm-venv/bin/python ]\n[ -f /opt/gitm/native.py ]\n');pre.chmod(0o755)
  for name in ('postinst','postrm'):
   script=control/name;shutil.copy2(ROOT/'branding-update'/name,script);script.chmod(0o755)
  files=[f for folder in (app,stage/'usr',stage/'etc') for f in sorted(folder.rglob('*')) if f.is_file()]
  (control/'md5sums').write_text(''.join(hashlib.md5(f.read_bytes()).hexdigest()+'  '+str(f.relative_to(stage))+'\n' for f in files))
  package=a.output/'gitm-autodiag_3.4.0-2_all.deb';run('dpkg-deb','--root-owner-group','--build',stage,package)
  manifest={'package':package.name,'sha256':sha(package),'bytes':package.stat().st_size,'source_iso_sha256':EXPECTED,'preserves':'Runtime, system signing key and home directories are outside this package','files':{str(f.relative_to(stage)):sha(f) for f in files}}
  (a.output/'build-manifest.json').write_text(json.dumps(manifest,indent=2));(a.output/'SHA256SUMS').write_text(manifest['sha256']+'  '+package.name+'\n')
  print('PASS: application package built',package,manifest['sha256'])
if __name__=='__main__':main()

