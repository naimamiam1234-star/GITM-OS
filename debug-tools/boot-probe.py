import pathlib,subprocess,time
out=pathlib.Path('probe').resolve();out.mkdir(exist_ok=True)
iso=next(pathlib.Path('dist').glob('*.iso')).resolve();log=out/'serial.log'
p=subprocess.Popen(['qemu-system-x86_64','-accel','tcg','-m','4096','-smp','2','-cdrom',str(iso),'-boot','d','-display','none','-serial','stdio','-device','virtio-vga'],stdin=subprocess.PIPE,stdout=log.open('wb'),stderr=(out/'qemu.log').open('wb'))
try:
 deadline=time.monotonic()+120
 while time.monotonic()<deadline:
  if '(initramfs)' in log.read_text(errors='replace'):break
  time.sleep(1)
 command="uname -r; cat /conf/modules; /sbin/modprobe -v overlay; cat /proc/filesystems; ls /lib/modules; dmesg | tail -40; echo __PROBE_END__\n"
 p.stdin.write(command.encode());p.stdin.flush();time.sleep(5)
 print(log.read_text(errors='replace')[-18000:],flush=True)
finally:
 p.terminate();p.wait(timeout=10)
