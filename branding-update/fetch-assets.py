"""Materialize pinned user-supplied assets and SDK source archives for packaging."""
import hashlib,json,pathlib,urllib.request,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
def fetch(row,target):
 target=pathlib.Path(target);target.parent.mkdir(parents=True,exist_ok=True)
 if target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest()==row['sha256']:return
 temporary=target.with_suffix(target.suffix+'.download');digest=hashlib.sha256();total=0
 with urllib.request.urlopen(urllib.request.Request(row['url'],headers={'User-Agent':'GITM-resource-build/3.4'}),timeout=90) as response,temporary.open('wb') as out:
  while chunk:=response.read(1024*1024):
   total+=len(chunk)
   if total>row['bytes']:raise ValueError('Download exceeds pinned size')
   digest.update(chunk);out.write(chunk)
 if total!=row['bytes'] or digest.hexdigest()!=row['sha256']:raise ValueError('Pinned asset integrity failed: '+target.name)
 temporary.replace(target)
def main():
 guide=ROOT/'branding-update/downloads/Resource-Guide-and-Manifests.zip'
 fetch(json.loads((ROOT/'branding-update/guide-source.json').read_text()),guide)
 destination=ROOT/'diag-integration/resources/guides';destination.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(guide) as archive:
  if archive.testzip():raise ValueError('Resource guide CRC failed')
  for entry in archive.infolist():
   name=pathlib.PurePosixPath(entry.filename)
   if name.name==entry.filename and name.suffix in ('.json','.md') and entry.file_size<4000000:
    (destination/name.name).write_bytes(archive.read(entry))
 assets=ROOT/'diag-integration/assets/branding'
 for row in json.loads((ROOT/'branding-update/asset-sources.json').read_text()):
  target=(assets/row['path']).resolve()
  if not target.is_relative_to(assets.resolve()):raise ValueError('Invalid asset path')
  fetch(row,target)
 sources=ROOT/'branding-update/downloads/sdk';sources.mkdir(parents=True,exist_ok=True)
 for row in json.loads((ROOT/'branding-update/sdk-sources.json').read_text()):
  fetch(dict(row,url=row['archive_url']),sources/row['file'])
  with zipfile.ZipFile(sources/row['file']) as archive:
   if archive.testzip():raise ValueError('SDK archive CRC failed')
 pinned=json.loads((ROOT/'branding-update/obdb-source.json').read_text());folder=ROOT/'branding-update/downloads/obdb-parts';folder.mkdir(parents=True,exist_ok=True)
 for row in pinned['parts']:fetch(row,folder/row['file'])
 target=ROOT/'branding-update/downloads/OBDb-Vehicle-Definitions.zip'
 with target.open('wb') as out:
  for row in pinned['parts']:
   with (folder/row['file']).open('rb') as part:
    while chunk:=part.read(1024*1024):out.write(chunk)
 if target.stat().st_size!=pinned['bytes'] or hashlib.sha256(target.read_bytes()).hexdigest()!=pinned['sha256']:raise ValueError('OBDb archive reconstruction hash mismatch')
 print('PASS: 22 identity assets and 12 SDK source archives match pinned hashes')
if __name__=='__main__':main()
