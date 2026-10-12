#!/usr/bin/env python3
import hashlib,pathlib,urllib.request
url='https://res.cloudinary.com/b9fcbcfz/image/upload/v1791581159/gitm-os/desktop-3-3.png'
expected='fc25469daffa380285555d8ce25116297b4d03e0d168604bb2787008ddb3b973'
b=urllib.request.urlopen(url,timeout=90).read()
if hashlib.sha256(b).hexdigest()!=expected:raise RuntimeError('Wallpaper checksum mismatch')
p=pathlib.Path('build-input/app/assets/desktop/wallpaper.png');p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
