#!/bin/bash
set -Eeuo pipefail
root=$1
project=$PWD
mkdir -p "$root/var/tmp/gitm-theme-src" "$root/usr/share/doc/gitm-theme"
# Immutable upstream revisions; preserve source and licence notices in the release.
if [[ -x "$root/usr/bin/klassy-settings" ]] && grep -q 9b788b2ea8d40c6a7af3b0130de9e891d41fbb30 "$root/usr/share/doc/gitm-theme/SOURCES" 2>/dev/null; then
  echo 'Reusing verified pinned theme binaries'
else
curl -fL --retry 3 https://codeload.github.com/paulmcauley/klassy/tar.gz/9b788b2ea8d40c6a7af3b0130de9e891d41fbb30 | tar xz -C "$root/var/tmp/gitm-theme-src"
curl -fL --retry 3 https://codeload.github.com/luisbocanegra/plasma-panel-colorizer/tar.gz/d0b1d4cab773f05cdcda2c1b2970093a5c367b54 | tar xz -C "$root/var/tmp/gitm-theme-src"
chroot "$root" dpkg-query -W -f='${binary:Package}\n' > "$root/var/tmp/gitm-theme-existing"
chroot "$root" env DEBIAN_FRONTEND=noninteractive bash <<'ROOT'
set -Eeuo pipefail
apt-get update
apt-get install -y xdotool papirus-icon-theme language-pack-kde-ar language-pack-kde-fr cmake ninja-build g++ extra-cmake-modules qt6-base-dev qt6-svg-dev qt6-declarative-dev libkf6coreaddons-dev libkf6colorscheme-dev libkf6config-dev libkf6guiaddons-dev libkf6i18n-dev libkf6iconthemes-dev libkf6windowsystem-dev libkf6kcmutils-dev libkf6style-dev libkdecorations3-dev libplasma-dev
cmake -S /var/tmp/gitm-theme-src/klassy-* -B /var/tmp/gitm-theme-src/klassy-build -G Ninja -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_BUILD_TYPE=Release -DBUILD_QT5=OFF -DBUILD_TESTING=OFF -DKDE_INSTALL_USE_QT_SYS_PATHS=ON
cmake --build /var/tmp/gitm-theme-src/klassy-build -j2
cmake --install /var/tmp/gitm-theme-src/klassy-build
cmake -S /var/tmp/gitm-theme-src/plasma-panel-colorizer-* -B /var/tmp/gitm-theme-src/colorizer-build -G Ninja -DCMAKE_INSTALL_PREFIX=/usr -DBUILD_PLUGIN=ON -DINSTALL_PLASMOID=ON
cmake --build /var/tmp/gitm-theme-src/colorizer-build -j2
cmake --install /var/tmp/gitm-theme-src/colorizer-build
ROOT
cp -a "$root"/var/tmp/gitm-theme-src/klassy-9*/LICENSES "$root/usr/share/doc/gitm-theme/klassy-licenses"
cp -a "$root"/var/tmp/gitm-theme-src/plasma-panel-colorizer-*/LICENSE* "$root/usr/share/doc/gitm-theme/"
printf '%s\n' 'Klassy source: https://github.com/paulmcauley/klassy/tree/9b788b2ea8d40c6a7af3b0130de9e891d41fbb30' 'Panel Colorizer source: https://github.com/luisbocanegra/plasma-panel-colorizer/tree/d0b1d4cab773f05cdcda2c1b2970093a5c367b54' 'Papirus: Ubuntu papirus-icon-theme package, see /usr/share/doc/papirus-icon-theme' > "$root/usr/share/doc/gitm-theme/SOURCES"
fi
# Official Mozilla DEB repository, signature fingerprint checked before use.
chroot "$root" env DEBIAN_FRONTEND=noninteractive bash <<'FIREFOX'
set -Eeuo pipefail
apt-get update
apt-get install -y ca-certificates curl gnupg pavucontrol pulseaudio-utils
install -d -m755 /etc/apt/keyrings
curl -fL --retry 3 https://packages.mozilla.org/apt/repo-signing-key.gpg -o /etc/apt/keyrings/packages.mozilla.org.asc
fingerprint=$(gpg --batch --show-keys --with-colons /etc/apt/keyrings/packages.mozilla.org.asc | awk -F: '$1=="fpr" {print $10;exit}')
test "$fingerprint" = 35BAA0B33E9EB396F59CA838C0BA5CE6DC6315A3
cat > /etc/apt/sources.list.d/mozilla.sources <<'APT'
Types: deb
URIs: https://packages.mozilla.org/apt
Suites: mozilla
Components: main
Signed-By: /etc/apt/keyrings/packages.mozilla.org.asc
APT
cat > /etc/apt/preferences.d/mozilla <<'APT'
Package: *
Pin: origin packages.mozilla.org
Pin-Priority: 1000

Package: firefox
Pin: release o=Ubuntu
Pin-Priority: -1
APT
apt-get update
apt-get install -y firefox firefox-l10n-ar firefox-l10n-fr
apt-get purge -y falkon
command -v firefox
test -x /usr/lib/firefox/firefox
test -f /usr/share/applications/firefox.desktop
test "$(dpkg-query -W -f='${Installed-Size}' firefox)" -gt 50000
FIREFOX
install -m644 patches/desktop_radios.py "$root/opt/gitm/desktop_radios.py"
install -m644 "$root/usr/share/icons/Papirus/64x64/apps/firefox.svg" "$root/opt/gitm/assets/desktop/browser.svg"
install -m644 theme-integration/install.svg "$root/opt/gitm/assets/desktop/install.svg"
mkdir -p "$root/etc/skel/.config"
cat > "$root/etc/skel/.config/mimeapps.list" <<'MIME'
[Default Applications]
x-scheme-handler/http=firefox.desktop;
x-scheme-handler/https=firefox.desktop;
text/html=firefox.desktop;
MIME
chmod 755 "$root/usr/share/plasma/plasmoids/luisbocanegra.panel.colorizer/contents/ui/tools/list_presets.sh" "$root/usr/share/plasma/plasmoids/luisbocanegra.panel.colorizer/contents/ui/tools/gdbus_get_signal.sh"
sed -i 's|^Icon=.*|Icon=/opt/gitm/assets/desktop/engine.svg|' "$root/usr/share/applications/gitm-autodiag.desktop"
sed -i '/^StartupWMClass=/d' "$root/usr/share/applications/gitm-autodiag.desktop"
printf '\nStartupWMClass=gitm-autodiag\n' >> "$root/usr/share/applications/gitm-autodiag.desktop"
install -m644 plasma-transition/patches/gitm_desktop.py "$root/opt/gitm/gitm_desktop.py"
install -D -m644 theme-integration/layout.js "$root/usr/share/plasma/look-and-feel/org.gitm.desktop/contents/layouts/org.kde.plasma.desktop-layout.js"
# Seed matching native app style, decoration and icons, without upstream layout overrides.
mkdir -p "$root/etc/skel/.config"
cat > "$root/etc/skel/.config/kdeglobals" <<'CFG'
[KDE]
LookAndFeelPackage=org.gitm.desktop
widgetStyle=klassy
[Icons]
Theme=Papirus-Dark
[General]
ColorScheme=BreezeDark
[Locale]
Language=ar:fr:en_US
CFG
cat > "$root/etc/skel/.config/kwinrc" <<'CFG'
[org.kde.kdecoration2]
library=org.kde.klassy
[Plugins]
blurEnabled=true
CFG
cat > "$root/usr/share/applications/gitm-desktop.desktop" <<'DESKTOP'
[Desktop Entry]
Type=Application
Name=GITM OS
Exec=gitm-desktop
Icon=gitm-more
NoDisplay=true
StartupWMClass=gitm-desktop
DESKTOP
# Native calculator from desktop; AutoDiag retains its clearly scoped workshop calculator.
install -m644 patches/gallery_runner.py "$root/opt/gitm/gallery_runner.py"
python3 - "$root/opt/gitm/gallery_runner.py" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]);s=p.read_text().replace('systemsettings5','systemsettings').replace('Falkon','Firefox')
s=s.replace(" def cleanup(self):\n", " def cleanup(self):\n  subprocess.run(['xdotool','mousemove','640','80'],check=False)\n")
s=s.replace("QTimer.singleShot(10000 if", "QTimer.singleShot(35000 if name=='system-updates' else 10000 if")
s=s.replace(" def capture(self,name):\n", " def capture(self,name):\n  if name in {'desktop','desktop-light'}:\n   subprocess.run(['xdotool','mousemove','640','799'],check=False);__import__('time').sleep(0.8)\n  if name=='settings':\n   self.w.settings();self.w.choose_appearance()\n   native=[line for line in windows() if 'System Settings' in line or 'إعدادات النظام' in line or 'إعدادات النّظام' in line]\n   emit('GITM_SETTINGS_WINDOWS|'+str(len(native)))\n   if len(native)!=1:emit('GITM_GALLERY_ERROR|settings|Expected one native settings window')\n")
p.write_text(s)
PY
# Ensure the installed native binaries/plugins actually exist before repacking.
chroot "$root" bash -c 'command -v klassy-settings; find /usr/lib -name "org.kde.klassy.so" -o -name "klassy.so"; test -d /usr/share/plasma/plasmoids/luisbocanegra.panel.colorizer; test -d /usr/share/icons/Papirus-Dark'
rm -rf "$root/var/tmp/gitm-theme-src"
chroot "$root" apt-get clean
# Give AutoDiag a real launcher identity and icon on the native task manager.
python3 - "$root/opt/gitm/native.py" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]);s=p.read_text()
pos=s.index("        self.setWindowTitle(")
s=s if "QApplication.setApplicationName('gitm-autodiag')" in s else s[:pos]+"        from PySide6.QtGui import QIcon\n        from pathlib import Path\n        QApplication.setDesktopFileName('gitm-autodiag')\n        QApplication.setApplicationName('gitm-autodiag')\n        self.setWindowIcon(QIcon(str(Path(__file__).parent/'assets/desktop/engine.svg')))\n"+s[pos:]
p.write_text(s);compile(s,str(p),'exec')
PY

