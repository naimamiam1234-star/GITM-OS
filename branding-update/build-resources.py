"""Package source archives and reference data, without executing archived code."""
import hashlib,io,json,pathlib,shutil,subprocess,sys,tempfile,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
def package(stage,name,out):
 control=stage/'DEBIAN';control.mkdir();version='2026.10.13-1'
 (control/'control').write_text(f'Package: {name}\nVersion: {version}\nArchitecture: all\nMaintainer: GITM OS Project\nDescription: GITM reference sources with original license files\n No automatic vehicle commands or device driver activation.\n')
 files=[p for p in sorted((stage/'opt').rglob('*')) if p.is_file()]
 (control/'md5sums').write_text(''.join(hashlib.md5(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(stage))+'\n' for p in files))
 target=out/f'{name}_{version}_all.deb';subprocess.run(['dpkg-deb','--root-owner-group','--build',str(stage),str(target)],check=True)
 return {'package':target.name,'bytes':target.stat().st_size,'sha256':sha(target),'files':len(files)}
def licenses(archive):return [n for n in archive.namelist() if pathlib.PurePosixPath(n).name.lower().startswith(('license','licence','copying'))]
def build(out):
 out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=True);results=[]
 with tempfile.TemporaryDirectory(prefix='gitm-resources-') as temp:
  temp=pathlib.Path(temp);sdk=temp/'sdk';root=sdk/'opt/gitm/resources';(root/'sdk').mkdir(parents=True);catalog=[]
  for row in json.loads((ROOT/'branding-update/sdk-sources.json').read_text()):
   source=ROOT/'branding-update/downloads/sdk'/row['file']
   if sha(source)!=row['sha256']:raise ValueError('SDK source hash mismatch')
   with zipfile.ZipFile(source) as archive:
    if archive.testzip() or not licenses(archive):raise ValueError('SDK source license or CRC missing')
   shutil.copy2(source,root/'sdk'/row['file']);catalog.append({'name':row['file'],'category':'SDK source archive','source_url':row['source'],'path':'sdk/'+row['file'],'sha256':row['sha256'],'license_files':row['license_files'],'integration_verified':False,'status':'source files available; hardware integration not validated'})
  (root/'catalog-sdk.json').write_text(json.dumps(catalog,indent=2));results.append(package(sdk,'gitm-sdk-sources',out))
  source=ROOT/'branding-update/downloads/OBDb-Vehicle-Definitions.zip';pinned=json.loads((ROOT/'branding-update/obdb-source.json').read_text())
  if sha(source)!=pinned['sha256']:raise ValueError('OBDb source archive hash mismatch')
  stage=temp/'obdb';root=stage/'opt/gitm/resources';(root/'obdb').mkdir(parents=True);catalog=[];installed=0
  with zipfile.ZipFile(source) as archive:
   status={r['file']:r['repository'] for r in json.loads(archive.read('download-status.json')) if 'file' in r and 'repository' in r}
   for name in archive.namelist():
    if not name.endswith('.zip') or pathlib.PurePosixPath(name).name!=name:continue
    raw=archive.read(name);summary={'definitions':0,'commands_defined':0,'ecu_types':[]}
    with zipfile.ZipFile(io.BytesIO(raw)) as inner:
     if inner.testzip():raise ValueError('Nested OBDb CRC failed')
     found=licenses(inner)
     for entry in inner.infolist():
      if '/signalsets/' not in entry.filename or not entry.filename.endswith('.json') or entry.file_size>2*1024*1024:continue
      try:value=json.loads(inner.read(entry))
      except (ValueError,UnicodeError):continue
      if not isinstance(value,dict):continue
      summary['definitions']+=1;summary['commands_defined']+=len(value.get('commands',[])) if isinstance(value.get('commands'),list) else 0
      for ecu in value.get('ecu',[]) if isinstance(value.get('ecu'),list) else []:
       if isinstance(ecu,dict) and isinstance(ecu.get('type'),str) and ecu['type'] not in summary['ecu_types']:summary['ecu_types'].append(ecu['type'])
    if found:(root/'obdb'/name).write_bytes(raw);installed+=1
    catalog.append({'name':name.removesuffix('.zip'),'category':'OBDb reference','source_url':'https://github.com/'+status.get(name,'OBDb/'+name.removesuffix('.zip')),'path':'obdb/'+name if found else None,'sha256':hashlib.sha256(raw).hexdigest(),'license_files':found,'profile_summary':summary,'integration_verified':False,'status':'reference definitions, not vehicle validation' if found else 'link only; license file not found','year_policy':'Diagnostic filters are not imported as vehicle production years'})
  (root/'catalog-obdb.json').write_text(json.dumps(catalog,indent=2));results.append(package(stage,'gitm-obdb-data',out));results[-1].update(index_records=len(catalog),bundled_archives=installed,link_only=len(catalog)-installed)
  (out/'resource-manifest.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))
if __name__=='__main__':build(sys.argv[1])
