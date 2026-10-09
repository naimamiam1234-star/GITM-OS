import urllib.request,urllib.error,json,hashlib,time
urllib.request.install_opener(urllib.request.build_opener())
urllib.request._opener.addheaders=[("User-Agent","Mozilla/5.0 GITM-ISO-verification")]
BASE="https://gitm-os-download-33.naimamiam1234.workers.dev"
try:
 m=json.load(urllib.request.urlopen(BASE+"/manifest.json",timeout=90))
except urllib.error.HTTPError as e:
 print("Manifest HTTP error",e.code,e.headers,e.read(4096).decode(errors="replace"),flush=True);raise
url=BASE+"/"+m["name"]
def read_range(value):
 r=urllib.request.urlopen(urllib.request.Request(url,headers={"Range":value}),timeout=90)
 assert r.status==206,(r.status,r.headers)
 return r.read()
assert read_range("bytes=32769-32773")==b"CD001"
assert read_range("bytes=%d-%d"%(m["boundary_offset"],m["boundary_offset"]+31)).hex()==m["boundary_hex"]
assert read_range("bytes=-32").hex()==m["tail_hex"]
r=urllib.request.urlopen(urllib.request.Request(url,method="HEAD"),timeout=90)
assert int(r.headers["Content-Length"])==m["size"]
for value in ["bytes=999999999999-","bytes=9-2","bytes=1-2,5-6"]:
 try: read_range(value);raise AssertionError("invalid range accepted")
 except urllib.error.HTTPError as e:assert e.code==416
print("HEAD, ISO signature, split boundary, suffix and invalid ranges passed",flush=True)
sha=hashlib.sha256();count=0
with urllib.request.urlopen(url,timeout=120) as response:
 while True:
  block=response.read(1024*1024)
  if not block:break
  sha.update(block);count+=len(block)
assert count==m["size"],(count,m["size"])
assert sha.hexdigest()==m["sha256"],sha.hexdigest()
print("FULL_ISO_SHA256_VERIFIED",count,sha.hexdigest(),flush=True)
