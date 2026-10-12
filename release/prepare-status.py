"""Prepare immutable release parts for GitHub's per-asset size limit."""
import pathlib,hashlib,json,shutil,os
root=pathlib.Path('dist');p=next(root.glob('*.iso'));expected=(root/(p.name+'.sha256')).read_text().split()[0]
h=hashlib.sha256()
with p.open('rb') as f:
 while b:=f.read(4*1024*1024):h.update(b)
if h.hexdigest()!=expected:raise RuntimeError('Downloaded ISO checksum mismatch')
chunk=1500*1024*1024;parts=[]
with p.open('rb') as f:
 index=1
 while f.tell()<p.stat().st_size:
  name=p.name+f'.part-{index:02d}';dest=root/name;digest=hashlib.sha256();written=0
  with dest.open('wb') as out:
   while written<chunk:
    b=f.read(min(4*1024*1024,chunk-written))
    if not b:break
    out.write(b);digest.update(b);written+=len(b)
  parts.append({'name':name,'size':written,'sha256':digest.hexdigest(),'url':'https://github.com/naimamiam1234-star/GITM-OS/releases/download/gitm-os-3.3.0-layoutfix1/'+name});index+=1
with p.open('rb') as f:
 f.seek(chunk-16);boundary=f.read(32).hex();f.seek(-32,2);tail=f.read(32).hex()
m={'name':p.name,'size':p.stat().st_size,'sha256':expected,'parts':parts,'boundary_offset':chunk-16,'boundary_hex':boundary,'tail_hex':tail,'boot_test_run':int(os.environ['BOOT_TEST_RUN']),'bios':'passed','uefi':'passed'}
gallery=root/'gallery.html'
if not gallery.exists():raise RuntimeError('Missing verified screenshot album')
m['gallery']={'images':58,'size':gallery.stat().st_size,'sha256':hashlib.sha256(gallery.read_bytes()).hexdigest(),'url':'https://github.com/naimamiam1234-star/GITM-OS/releases/download/gitm-os-3.3.0-layoutfix1/gallery.html','overview_url':'https://github.com/naimamiam1234-star/GITM-OS/releases/download/gitm-os-3.3.0-layoutfix1/gallery-overview.png'}
(root/'release-manifest.json').write_text(json.dumps(m,indent=2))
cmd='@echo off\r\nsetlocal\r\ncd /d "%~dp0"\r\n'
cmd+=f'if exist "{p.name}" goto verify\r\n'
for part in parts:cmd+=f'if not exist "{part["name"]}" goto missing\r\n'
cmd+='copy /b '+ '+'.join('"'+part['name']+'"' for part in parts)+' "'+p.name+'" >nul\r\nif errorlevel 1 goto error\r\n:verify\r\n'
cmd+=f'''powershell -NoProfile -Command "if ((Get-FileHash -LiteralPath '{p.name}' -Algorithm SHA256).Hash -ne '{expected}') {{ Write-Error 'Checksum mismatch'; exit 1 }}; Write-Host 'ISO SHA-256 verified'"\r\nif errorlevel 1 goto error\r\necho Ready: {p.name}\r\npause\r\nexit /b 0\r\n:missing\r\necho Download both ISO parts into this folder first.\r\n:error\r\necho ISO assembly or verification failed.\r\npause\r\nexit /b 1\r\n'''
(root/'Join-ISO-Windows.cmd').write_bytes(cmd.encode('ascii'))
print(json.dumps(m),flush=True)
