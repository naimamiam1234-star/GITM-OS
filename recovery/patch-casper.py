#!/usr/bin/env python3
"""Validate filesystem support rather than Casper's optional modprobe argv."""
import pathlib,sys
root=pathlib.Path(sys.argv[1]);p=root/'usr/share/initramfs-tools/scripts/casper'
s=p.read_text();lines=s.splitlines();count=0;out=[]
for line in lines:
 if 'modprobe' in line and 'panic' in line and 'overlay' in line and 'no support found' in line:
  indent=line[:len(line)-len(line.lstrip())]
  out.extend([indent+'if ! grep -qw overlay /proc/filesystems; then modprobe overlay || true; fi',indent+'grep -qw overlay /proc/filesystems || panic "Overlay filesystem unavailable"'])
  count+=1
 else:out.append(line)
if count!=1:raise RuntimeError('Casper source drift: expected one overlay modprobe guard, got '+str(count))
p.write_text('\n'.join(out)+'\n')
print('Casper overlay guard repaired; absence of filesystem support still fails boot')
