#!/usr/bin/env python3
"""Append a diagnostic hook AND its preserved initramfs-tools ORDER entry.

Reads newc archives in memory without extracting their paths. Supports leading
uncompressed microcode archives followed by gzip, xz or zstd initramfs members.
"""
import argparse
import gzip
import hashlib
import json
import lzma
from pathlib import Path
import re
import stat
import zlib

LIMIT = 1024 * 1024 * 1024
SELECT = {'scripts/functions', 'scripts/casper-bottom/ORDER'}
HOOK_NAME = 'scripts/casper-bottom/99gitm-installer-probe'

def archive(data, start, selected):
    pos = start
    while True:
        if data[pos:pos+6] not in (b'070701', b'070702') or pos+110 > len(data):
            raise ValueError('Invalid newc header at '+str(pos))
        fields = [int(data[pos+6+i*8:pos+14+i*8],16) for i in range(13)]
        size, namesize = fields[6], fields[11]
        begin = pos+110
        if namesize < 1 or begin+namesize > len(data):
            raise ValueError('Invalid newc filename extent')
        raw = data[begin:begin+namesize]
        if raw[-1:] != b'\0': raise ValueError('Unterminated newc filename')
        name = raw[:-1].decode('utf-8', errors='strict')
        # Names are compared only; never passed to filesystem extraction.
        while name.startswith('./'): name=name[2:]
        content = (begin+namesize+3)&~3
        end=content+size
        if end > len(data): raise ValueError('Truncated newc file')
        pos=(end+3)&~3
        if name=='TRAILER!!!': return pos
        if name in SELECT: selected[name]=data[content:end]

def inspect(data):
    pos=0; selected={}; members=[]
    while pos<len(data):
        while pos<len(data) and data[pos]==0: pos+=1
        if pos==len(data): break
        if data[pos:pos+6] in (b'070701',b'070702'):
            end=archive(data,pos,selected); members.append({'kind':'newc','offset':pos,'bytes':end-pos});pos=end;continue
        rest=data[pos:]
        if rest.startswith(b'\x1f\x8b'):
            dec=zlib.decompressobj(31); plain=dec.decompress(rest,LIMIT+1)
            if len(plain)>LIMIT or not dec.eof: raise ValueError('gzip member exceeds limit or is truncated')
            unused=dec.unused_data; kind='gzip'
        elif rest.startswith(b'\xfd7zXZ\0'):
            dec=lzma.LZMADecompressor();plain=dec.decompress(rest,max_length=LIMIT+1)
            if len(plain)>LIMIT or not dec.eof: raise ValueError('xz member exceeds limit or is truncated')
            unused=dec.unused_data;kind='xz'
        elif rest.startswith(b'\x28\xb5\x2f\xfd'):
            try: import zstandard
            except ImportError: raise ValueError('zstd initramfs requires Python zstandard')
            dec=zstandard.ZstdDecompressor().decompressobj();plain=dec.decompress(rest)
            if len(plain)>LIMIT or not dec.eof: raise ValueError('zstd member exceeds limit or is truncated')
            unused=dec.unused_data;kind='zstd'
        else: raise ValueError('Unsupported initramfs member magic at '+str(pos)+': '+rest[:8].hex())
        inner=0
        while inner<len(plain):
            while inner<len(plain) and plain[inner]==0: inner+=1
            if inner==len(plain):break
            inner=archive(plain,inner,selected)
        consumed=len(rest)-len(unused)
        members.append({'kind':kind,'offset':pos,'bytes':consumed,'uncompressed_bytes':len(plain)})
        pos+=consumed
    return selected,members

def cpio(files):
    result=bytearray();ino=0
    for name,mode,content in files+[('TRAILER!!!',0,b'')]:
        ino+=1; encoded=name.encode()+b'\0'
        fields=[ino,mode,0,0,1,0,len(content),0,0,0,0,len(encoded),0]
        result.extend(b'070701'+''.join(f'{v:08x}' for v in fields).encode())
        result.extend(encoded);result.extend(b'\0'*((-len(result))%4))
        result.extend(content);result.extend(b'\0'*((-len(result))%4))
    result.extend(b'\0'*((-len(result))%512));return bytes(result)

HOOK = b'''#!/bin/sh
PREREQ=""
case "$1" in prereqs) echo "$PREREQ"; exit 0;; esac
target=${rootmnt:-/root}
echo "GITM_INSTALL_PROBE|INITRD_HOOK|target=$target" >/dev/ttyS0
mkdir -p "$target/usr/local/lib/gitm-probe" "$target/etc/systemd/system/multi-user.target.wants"
cp /gitm-probe/guest-probe.py "$target/usr/local/lib/gitm-probe/guest-probe.py"
cat > "$target/etc/systemd/system/gitm-installer-probe.service" <<'UNIT'
[Unit]
Description=Test-only non-writing installer startup probe
After=display-manager.service
[Service]
Type=simple
ExecStart=/usr/bin/python3 /usr/local/lib/gitm-probe/guest-probe.py
TimeoutStopSec=5
[Install]
WantedBy=multi-user.target
UNIT
ln -sf /etc/systemd/system/gitm-installer-probe.service "$target/etc/systemd/system/multi-user.target.wants/gitm-installer-probe.service"
echo "GITM_INSTALL_PROBE|INITRD_HOOK|installed" >/dev/ttyS0
'''

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('original',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--helper',type=Path,default=Path(__file__).with_name('guest-probe.py'))
    parser.add_argument('--inspect-only',action='store_true')
    args=parser.parse_args();original=args.original.read_bytes()
    selected,members=inspect(original)
    order=selected.get('scripts/casper-bottom/ORDER')
    functions=selected.get('scripts/functions',b'').decode(errors='replace')
    match=re.search(r'run_scripts\(\)\s*\{(.*?)\n\}',functions,re.S)
    snippet=match.group(0) if match else ''
    report={'source_sha256':hashlib.sha256(original).hexdigest(),'members':members,
            'run_scripts_source':snippet,'casper_bottom_ORDER':order.decode(errors='replace') if order is not None else None}
    if order is None: raise ValueError('Missing original casper-bottom/ORDER; refusing to replace unknown ordering')
    if not snippet or 'ORDER' not in snippet: raise ValueError('Cannot verify actual initramfs run_scripts ORDER dispatch')
    if HOOK_NAME.encode() in order: raise ValueError('Hook already present in original ORDER')
    updated=order.rstrip(b'\n')+b'\n/'+HOOK_NAME.encode()+b' "$@"\n[ -e /conf/param.conf ] && . /conf/param.conf\n'
    report['patched_ORDER']=updated.decode()
    if not args.inspect_only:
        files=[(name,stat.S_IFDIR|0o755,b'') for name in ['scripts','scripts/casper-bottom','gitm-probe']]
        files += [('scripts/casper-bottom/ORDER',stat.S_IFREG|0o644,updated),
                  (HOOK_NAME,stat.S_IFREG|0o755,HOOK),
                  ('gitm-probe/guest-probe.py',stat.S_IFREG|0o644,args.helper.read_bytes())]
        tail=gzip.compress(cpio(files),compresslevel=1,mtime=0)
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_bytes(original+tail)
        roundtrip,_=inspect(args.output.read_bytes())
        if roundtrip['scripts/casper-bottom/ORDER']!=updated: raise RuntimeError('Appended ORDER failed roundtrip verification')
        report['output_sha256']=hashlib.sha256(args.output.read_bytes()).hexdigest()
        report['appended_bytes']=len(tail)
    args.output.with_suffix(args.output.suffix+'.injection.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
