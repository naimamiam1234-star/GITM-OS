#!/usr/bin/env python3
"""Recover the exact user-provided source snapshot; never execute archive scripts."""
import hashlib, html.parser, pathlib, urllib.parse, urllib.request, zipfile
FILE_ID='1NxV6XIJd2nuQeUI53s8aYA51Koo6dwWW'
SHA256='bcab16e7a85a5b2e29c0e74c1e519a6067dd6d7dbabe25bc6b088231a9f42ad3'
class Form(html.parser.HTMLParser):
 def __init__(self):super().__init__();self.action=None;self.fields={}
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='form':self.action=a.get('action')
  if tag=='input' and a.get('name'):self.fields[a['name']]=a.get('value','')
def main():
 target=pathlib.Path('build-input');target.mkdir(exist_ok=True)
 url='https://drive.google.com/uc?'+urllib.parse.urlencode({'export':'download','id':FILE_ID})
 with urllib.request.urlopen(url,timeout=60) as r:
  first=r.read(65536)
  if first.startswith(b'PK'):
   with (target/'source.zip').open('wb') as f:
    f.write(first)
    while chunk:=r.read(1024*1024):f.write(chunk)
  else:
   form=Form();form.feed(first.decode())
   if not form.action or urllib.parse.urlparse(form.action).hostname!='drive.usercontent.google.com':raise RuntimeError('Drive download confirmation unavailable')
   url=form.action+'?'+urllib.parse.urlencode(form.fields)
   with urllib.request.urlopen(url,timeout=120) as response,(target/'source.zip').open('wb') as f:
    while chunk:=response.read(1024*1024):f.write(chunk)
 archive=target/'source.zip'
 if hashlib.sha256(archive.read_bytes()).hexdigest()!=SHA256:raise RuntimeError('Source SHA-256 mismatch')
 with zipfile.ZipFile(archive) as z:
  for item in z.infolist():
   if not (item.filename.startswith('app/') or item.filename=='overlay/usr/share/gitm/update-public.pem'):continue
   if pathlib.PurePosixPath(item.filename).is_absolute() or '..' in pathlib.PurePosixPath(item.filename).parts:raise RuntimeError('Unsafe archive member')
   z.extract(item,target)
 print('Pinned source recovered; data licences remain in app/data/external.')
if __name__=='__main__':main()
