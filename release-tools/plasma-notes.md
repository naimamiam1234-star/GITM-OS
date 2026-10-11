GITM OS Plasma 6 preview, based on Ubuntu 26.04 LTS (amd64).

The bundled Qt runtime requires SSSE3, SSE4.1, SSE4.2 and POPCNT CPU support.

Runs a native Plasma X11 session with KWin and the GITM home screen. Includes the existing GITM AutoDiag application. The release workflow checks the ISO checksum, nonblack BIOS/UEFI guest framebuffers, actual mouse/keyboard search input and the captured application gallery.

This is a development preview. Installation on physical hardware, vehicle adapters, OEM coding, ADAS/key equipment, authenticated cloud services and complete system updates have not been validated by these guest tests.


The ISO is split into ordered parts because of GitHub's asset size limit. Download all parts and the checksum file into one directory, then assemble and verify:

```sh
cat GITM-OS-Plasma6-amd64.iso.part[0-9][0-9] > GITM-OS-Plasma6-amd64.iso
sha256sum -c GITM-OS-Plasma6-amd64.iso.sha256
```

This revision populates and preserves the Ubuntu APT/AppStream application catalogue in the live image. Build and guest checks require a populated repository catalogue, separately from the network HTTPS check.

The gallery ZIP contains screenshots captured from the running ISO guest. Opening the software centre does not validate installation of system updates or applications on physical hardware.

This revision integrates pinned Klassy window decorations/application style, Papirus icons and Panel Colorizer. The bottom panel becomes a centered floating dock that is visible by default (automatic hiding is optional through native panel settings) with native icon tasks, without a repeated bottom clock/system tray. Settings entry points use native System Settings; repeated activation is checked for a single window. Native colour-scheme light/dark changes synchronize the GITM home screen. Desktop calculator launches KCalc; AutoDiag receives its launcher identity and application icon.

Upstream sources/licences are retained in `/usr/share/doc/gitm-theme`. These guest checks do not establish every theme customization, touch interaction or physical-hardware behavior.

The native desktop and GITM workspace share the same wallpaper and screen crop. Status remains in the top bar; the bottom dock contains application controls only.

This revision replaces Falkon with the Mozilla Firefox DEB and sets the HTTP/HTTPS defaults. The top bar places a measured audio icon beside Wi-Fi and opens the real sound mixer. Connectivity commands recover from failed starts; Wi-Fi distinguishes a powered radio without a connection from a disabled or missing adapter. Missing battery uses a red X; absent radio/audio indicators use a neutral mark. Network and power dialogs reuse an open window. Power buttons have function icons and confirmations use Arabic labels. The native Plasma theme follows the active palette instead of staying on breeze-dark, and the day workspace blends its lower edge with the wallpaper. Hardware connection and actual suspend/reboot/shutdown remain outside these guest checks.
