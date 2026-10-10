GITM OS Plasma 6 preview, based on Ubuntu 26.04 LTS (amd64).

The bundled Qt runtime requires SSSE3, SSE4.1, SSE4.2 and POPCNT CPU support.

Runs a native Plasma X11 session with KWin and the GITM home screen. Includes the existing GITM AutoDiag application. The release workflow checks the ISO checksum, BIOS/UEFI guest session markers and the captured application gallery.

This is a development preview. Installation on physical hardware, vehicle adapters, OEM coding, ADAS/key equipment, authenticated cloud services and complete system updates have not been validated by these guest tests.

Known issue: Discover still reports that it cannot load its application catalogue in the captured guest, although NetworkManager connects and an HTTPS request to the Ubuntu repository succeeds. The screenshot gallery records this issue; the software centre is not considered validated.

The ISO is split into ordered parts because of GitHub's asset size limit. Download all parts and the checksum file into one directory, then assemble and verify:

```sh
cat GITM-OS-Plasma6-amd64.iso.part[0-9][0-9] > GITM-OS-Plasma6-amd64.iso
sha256sum -c GITM-OS-Plasma6-amd64.iso.sha256
```

The gallery ZIP contains screenshots captured from the running ISO guest.
