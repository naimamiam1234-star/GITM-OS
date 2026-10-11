"""Boot the exact release ISO and exercise real mouse/keyboard input via QMP."""
import base64,json,socket,subprocess,time
from pathlib import Path
from PIL import Image,ImageOps,ImageChops,ImageStat

iso=next(Path('download/iso').glob('*.iso')).resolve()
out=Path('input-check').resolve();out.mkdir(exist_ok=True)
qmp=out/'monitor.sock';serial=out/'serial.log'
args=['qemu-system-x86_64','-machine','q35,accel=kvm:tcg','-cpu','max','-m','4096','-smp','2','-cdrom',str(iso),'-boot','d','-display','none','-serial','file:'+str(serial),'-qmp','unix:'+str(qmp)+',server=on,wait=off','-device','virtio-vga','-device','qemu-xhci,id=xhci','-device','usb-tablet,bus=xhci.0']
p=subprocess.Popen(args,stdout=subprocess.DEVNULL,stderr=(out/'qemu.log').open('w'))
try:
 deadline=time.monotonic()+600
 while not qmp.exists():
  assert p.poll() is None,'QEMU exited'
  assert time.monotonic()<deadline,'QMP did not start'
  time.sleep(.1)
 s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);s.connect(str(qmp));f=s.makefile('rwb',buffering=0);f.readline()
 def command(execute,arguments=None):
  payload={'execute':execute}
  if arguments is not None:payload['arguments']=arguments
  f.write((json.dumps(payload)+'\n').encode())
  while True:
   reply=json.loads(f.readline())
   if 'error' in reply:raise RuntimeError(reply)
   if 'return' in reply:return reply['return']
 command('qmp_capabilities')
 print('GITM_INPUT_ACCELERATOR '+repr(command('query-kvm')),flush=True)
 while 'GITM_DESKTOP_VISIBLE' not in (serial.read_text(errors='replace') if serial.exists() else ''):
  assert p.poll() is None,'Guest exited'
  assert time.monotonic()<deadline,'No visible desktop'
  time.sleep(1)
 time.sleep(3)
 print('GITM_INPUT_SERIAL_TAIL '+serial.read_text(errors='replace')[-14000:],flush=True)
 print('GITM_INPUT_MICE '+repr(command('query-mice')),flush=True)
 command('send-key',{'keys':[{'type':'qcode','data':'shift'}]})
 def screenshot(name):
  ppm=out/(name+'.ppm');png=ppm.with_suffix('.png')
  command('screendump',{'filename':str(ppm)})
  Image.open(ppm).save(png);ppm.unlink();return png
 visual_deadline=time.monotonic()+120
 while True:
  initial=screenshot('desktop-before-input')
  from PIL import ImageStat
  if sum(ImageStat.Stat(Image.open(initial).convert('RGB')).mean)>30:break
  assert time.monotonic()<visual_deadline,'Visible desktop marker emitted but framebuffer remains black'
  command('send-key',{'keys':[{'type':'qcode','data':'shift'}]});time.sleep(5)
 width,height=Image.open(initial).size
 def move(x,y):
  command('input-send-event',{'events':[{'type':'abs','data':{'axis':'x','value':round(x*32767/(width-1))}},{'type':'abs','data':{'axis':'y','value':round(y*32767/(height-1))}}]})
 move(width//2,height-1);time.sleep(2);move(width//2,height-40);time.sleep(1);dock=screenshot('dock-revealed')
 print('GITM_NATIVE_DOCK_CAPTURED',flush=True)
 command('input-send-event',{'events':[{'type':'abs','data':{'axis':'x','value':round(400*32767/width)}},{'type':'abs','data':{'axis':'y','value':round(203*32767/height)}}]})
 for down in (True,False):
  command('input-send-event',{'events':[{'type':'btn','data':{'down':down,'button':'left'}}]});time.sleep(.15)
 def key(code):
  for down in (True,False):command('input-send-event',{'events':[{'type':'key','data':{'down':down,'key':{'type':'qcode','data':code}}}]})
  time.sleep(.1)
 for letter in 'calculator':key(letter)
 time.sleep(2)
 png=screenshot('keyboard-search')
 crop=Image.open(png).crop((35,177,min(960,width-30),230)).convert('RGB')
 crop=ImageOps.grayscale(crop).resize((crop.width*3,crop.height*3));crop.save(out/'search-text.png')
 result=subprocess.run(['tesseract',str(out/'search-text.png'),'stdout','--psm','7','-l','eng'],capture_output=True,text=True,check=True)
 (out/'ocr.txt').write_text(result.stdout)
 assert 'calculator' in ''.join(c for c in result.stdout.casefold() if c.isalpha()),'Keyboard text not present in the actual search field: '+repr(result.stdout)
 print('GITM_KEYBOARD_SEARCH_OK',flush=True)
 key('esc');time.sleep(1);screenshot('escape-cleared-search')
 def click(x,y):
  move(x,y)
  for down in (True,False):
   command('input-send-event',{'events':[{'type':'btn','data':{'down':down,'button':'left'}}]});time.sleep(.15)
 # Target the recorded 1280x800 desktop. Exclude clock, RAM ring and native dock.
 assert (width,height)==(1280,800),'Update popup input coordinates for the actual framebuffer'
 box=(420,80,1250,700)
 baseline=Image.open(screenshot('popup-baseline')).crop(box).convert('RGB')
 def difference(name):
  image=Image.open(screenshot(name)).crop(box).convert('RGB')
  return sum(ImageStat.Stat(ImageChops.difference(baseline,image)).mean)
 for name,x in [('volume',693),('wifi',748),('bluetooth',803),('power',1226),('control',1028)]:
  click(x,40);time.sleep(2)
  assert difference('popup-'+name)>3,name+' icon did not visibly open its popup'
  key('esc');time.sleep(.5)
  assert difference('popup-'+name+'-escape')<3,name+' popup did not close on Escape'
 click(693,40);time.sleep(1);click(803,40);time.sleep(1)
 assert difference('popup-switched-bluetooth')>3,'A single click did not switch between status icons'
 key('esc');time.sleep(.5)
 click(803,40);time.sleep(1);click(450,690);time.sleep(.5)
 assert difference('popup-outside-closed')<3,'Bluetooth popup did not close on outside click'
 print('GITM_POPUP_MOUSE_ESCAPE_OUTSIDE_OK',flush=True)
 (out/'result.txt').write_text('Actual release ISO booted; mouse focused the home search; physical scancodes entered calculator; OCR verified its rendered text. Escape screenshot captured for visual review.\n')
finally:
 print('GITM_INPUT_QEMU_LOG '+(out/'qemu.log').read_text(errors='replace'),flush=True)
 p.terminate()
 try:p.wait(timeout=10)
 except subprocess.TimeoutExpired:p.kill();p.wait()

