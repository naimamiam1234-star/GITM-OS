import sys
from pathlib import Path
sys.path.insert(0,str(Path('patches').resolve()))
from desktop_radios import classify_wifi
assert classify_wifi('wifi:disconnected:--',True,True)[1]['kind']=='on'
assert classify_wifi('wifi:unavailable:--',True,False)[1]['kind']=='off'
assert classify_wifi('ethernet:connected:Wired',True,True)[1]['kind']=='missing'
assert classify_wifi('',False,True)[1]['kind']=='error'
assert classify_wifi('wifi:connected:Workshop',True,True)[0]=='Workshop'
print('Wi-Fi disconnected, disabled, missing, service error and connected distinguished')
