#!/usr/bin/env python3
"""Gate and package gallery-only replacements for the unchanged source14 release."""
import copy,hashlib,json,pathlib,re,shutil,subprocess
P=pathlib.Path
SOURCE_RUN=38286238342; PUBLISHER_RUN=38286238297; RECAPTURE_RUN=38289500104
SOURCE_HEAD='e883ea6002479695714a9229c4c0deae5a453c34'
RECAPTURE_HEAD='546fd89b4bb619d9ec09760c959c48ea999feb3a'
def require(condition,message):
    if not condition:raise RuntimeError(message)
def one(root,pattern):
    matches=list(root.rglob(pattern));require(len(matches)==1,f'Expected exactly one {pattern} in {root}, found {len(matches)}');return matches[0]
def digest(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
root=P('download'); out=P('dist'); folder=out/'gallery'; assets=P('release-assets')
require(not folder.exists(),'Refusing reuse of staged gallery'); folder.mkdir(parents=True);assets.mkdir(exist_ok=True)
for run,head in [(RECAPTURE_RUN,RECAPTURE_HEAD),(PUBLISHER_RUN,SOURCE_HEAD),(SOURCE_RUN,SOURCE_HEAD)]:
    evidence=json.loads((root/'runs'/f'{run}.json').read_text())
    require(evidence['id']==run and evidence['head_sha']==head and evidence['status']=='completed' and evidence['conclusion']=='success',f'Run {run} identity/success gate failed')
manifest_path=one(root/'manifest','plasma-manifest.json'); manifest=json.loads(manifest_path.read_text()); before=copy.deepcopy(manifest)
require(manifest['build_commit']==SOURCE_HEAD and manifest['boot_test_run']==SOURCE_RUN,'Original release manifest is not exact source14')
fixture=json.loads(one(root/'recapture','fixture-report.json').read_text());require(fixture['iso_sha256']==manifest['sha256'],'Recapture ISO differs from release ISO')
iso_checks=one(root/'recapture','source14-iso.sha256').read_text().split()[0];require(iso_checks==manifest['sha256'],'Recapture source checksum mismatch')
report=one(root/'recapture','guest-report.txt').read_text();serial=one(root/'recapture','gallery-serial.log').read_text(errors='replace')
require('GITM_GALLERY_ERROR|' not in report+serial,'Recapture contains gallery failures')
require('GITM_GALLERY_INSTALLER_MINIMIZED|' in serial and 'GITM_GALLERY_INSTALLER_HIDDEN|PASS' in serial,'Missing minimize and visibility proof')
require('GITM_GALLERY_DONE' in serial,'Recapture did not finish')
images=list((one(root/'recapture','guest-report.txt').parent).glob('*.png'))
require(len(images)==69 and len({p.name for p in images})==69,'Expected exactly 69 unique recaptured gallery PNGs')
frames=re.findall(r'GITM_GALLERY_FRAME\|([a-z0-9-]+)',report)
require(len(frames)==69 and set(frames)=={p.stem for p in images},'Recapture report frames do not exactly match the 69 PNGs')
require(not any(p.name=='dock-revealed.png' for p in images),'Recapture unexpectedly includes publisher dock image')
dock=one(root/'input','dock-revealed.png')
results=list((root/'disk').rglob('result.json'));require(len(results)==2,'Expected exactly two final disk result files')
disk_proofs={}
for p in results:
    result=json.loads(p.read_text());mode=result.get('boot_mode')
    require(mode in {'BIOS','UEFI'} and mode not in disk_proofs,'Invalid or duplicate firmware result')
    require(result.get('install')=='pass' and result.get('disk_boot')=='pass' and result.get('live_media_removed') is True and result.get('disk_bytes')==40*1024**3,'Final disk installation or disk-only boot failed')
    sha=one(p.parent,'source-iso.sha256').read_text().split()[0];require(sha==manifest['sha256'],'Installed-test ISO differs from release ISO')
    shot=one(p.parent,'disk-boot-installed-autodiag.png')
    markers=one(p.parent,'disk-boot-markers.txt').read_text()
    require('GITM_INSTALL_TEST|DISK_BOOT_PASS' in markers and 'FRAME|installed-autodiag' in markers,'Missing installed AutoDiag/native boot proof')
    live=one(p.parent,'live-install-markers.txt').read_text()
    require('GITM_INSTALL_TEST|INSTALL_PASS' in live and 'TARGET_ROOT_PROOF|' in live,'Missing actual installation target proof')
    disk_proofs[mode]={'install':'passed','native_disk_boot':'passed','installed_autodiag_capture':'passed','iso_sha256':sha,'screenshot_sha256':digest(shot)}
require(set(disk_proofs)=={'BIOS','UEFI'},'Both BIOS and UEFI are required')
for p in images+[dock]:shutil.copy2(p,folder/p.name)
(folder/'guest-report.txt').write_text(report+'\nGITM_GALLERY_FRAME|dock-revealed\nGITM_GALLERY_CAPTURE_SOURCE|dock-revealed|publisher:'+str(PUBLISHER_RUN)+'\n')
subprocess.run(['python3','release-tools/prepare-gallery.py'],check=True)
for source,name in [(out/'gallery.zip','GITM-Plasma6-gallery.zip'),(out/'gallery.html','gallery.html'),(out/'gallery-overview.png','gallery-overview.png')]:shutil.copy2(source,assets/name)
gallery=manifest['gallery'];gallery.update({'images':70,'size':(assets/'gallery.html').stat().st_size,'sha256':digest(assets/'gallery.html'),'capture_runs':[RECAPTURE_RUN,PUBLISHER_RUN],'fixture_scope':'Original source14 ISO; transient test-only gallery cleanup minimizes installer and verifies hidden state before later frames'})
manifest['installed_disk_validation']={'run':PUBLISHER_RUN,'source_run':SOURCE_RUN,'source_commit':SOURCE_HEAD,'iso_sha256':manifest['sha256'],'firmware':disk_proofs}
require({k:v for k,v in manifest.items() if k not in {'gallery','installed_disk_validation'}}=={k:v for k,v in before.items() if k not in {'gallery','installed_disk_validation'}},'An immutable ISO manifest field changed')
(assets/'plasma-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
(out/'gallery-publication-review.json').write_text(json.dumps({'source_run':SOURCE_RUN,'recapture_run':RECAPTURE_RUN,'publisher_run':PUBLISHER_RUN,'iso_sha256':manifest['sha256'],'images':70,'assets':[{'name':p.name,'sha256':digest(p),'size':p.stat().st_size} for p in sorted(assets.iterdir())]},indent=2)+'\n')
print('NEW_GITM_RELEASE_MANIFEST '+json.dumps(manifest,separators=(',',':')),flush=True)
