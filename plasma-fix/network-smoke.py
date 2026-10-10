#!/usr/bin/python3
"""Read-only network check in the disposable gallery guest."""
import subprocess
import urllib.request

def emit(message):
    subprocess.run(['logger', '-t', 'gitm-network', message], check=False)

state = subprocess.run(['nmcli', '-t', '-f', 'STATE', 'general'], capture_output=True, text=True)
emit('GITM_NETWORK_STATE|' + state.stdout.strip())
try:
    with urllib.request.urlopen('https://archive.ubuntu.com/ubuntu/dists/resolute/Release', timeout=25) as response:
        data = response.read(2048)
        if response.status != 200 or b'Codename: resolute' not in data:
            raise RuntimeError('Unexpected Ubuntu repository response')
    emit('GITM_NETWORK_RELEASE_OK|resolute')
except Exception as error:
    emit('GITM_NETWORK_ERROR|' + str(error))
    raise
