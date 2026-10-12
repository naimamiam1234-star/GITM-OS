#!/usr/bin/env python3
"""Reject a catalogue containing only the small set of installed app metadata."""
import re
import sys

status = sys.stdin.read()
match = re.search(r'We have information on (\d+) software components', status)
if not match or int(match.group(1)) < 1000:
    raise SystemExit('Ubuntu application catalogue is missing or incomplete: ' + status)
print('GITM_CATALOG_COMPONENTS|' + match.group(1))
