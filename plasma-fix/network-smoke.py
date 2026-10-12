#!/usr/bin/python3
"""Read-only network check in the disposable gallery guest."""
import subprocess
import re
import urllib.request

def emit(message):
    subprocess.run(['logger', '-t', 'gitm-network', message], check=False)

state = subprocess.run(['nmcli', '-t', '-f', 'STATE', 'general'], capture_output=True, text=True)
emit('GITM_NETWORK_STATE|' + state.stdout.strip())
catalog = subprocess.run(['env', 'LC_ALL=C', 'appstreamcli', 'status'], capture_output=True, text=True, check=True)
components = re.search(r'We have information on (\d+) software components', catalog.stdout)
if not components or int(components.group(1)) < 1000:
    emit('GITM_CATALOG_ERROR|Ubuntu application catalogue missing')
    raise RuntimeError('Ubuntu application catalogue missing')
emit('GITM_CATALOG_COMPONENTS|' + components.group(1))
emit('GITM_CATALOG_OK')
try:
    with urllib.request.urlopen('https://archive.ubuntu.com/ubuntu/dists/resolute/Release', timeout=25) as response:
        data = response.read(2048)
        if response.status != 200 or b'Codename: resolute' not in data:
            raise RuntimeError('Unexpected Ubuntu repository response')
    emit('GITM_NETWORK_RELEASE_OK|resolute')
except Exception as error:
    emit('GITM_NETWORK_ERROR|' + str(error))
    raise
