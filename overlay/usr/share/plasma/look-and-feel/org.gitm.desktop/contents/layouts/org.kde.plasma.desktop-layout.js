var panel = new Panel;
panel.location = 'bottom';
panel.height = 56;
var launcher = panel.addWidget('org.kde.plasma.kickoff');
launcher.currentConfigGroup = ['General'];
launcher.writeConfig('icon', '/usr/share/icons/hicolor/scalable/apps/gitm-more.svg');
var tasks = panel.addWidget('org.kde.plasma.icontasks');
tasks.currentConfigGroup = ['General'];
tasks.writeConfig('launchers', ['applications:gitm-autodiag.desktop','applications:org.kde.dolphin.desktop','applications:org.kde.falkon.desktop','applications:org.kde.kcalc.desktop','applications:systemsettings.desktop']);
panel.addWidget('org.kde.plasma.systemtray');
panel.addWidget('org.kde.plasma.digitalclock');
for (var desktop of desktops()) {
 desktop.wallpaperPlugin = 'org.kde.image';
 desktop.currentConfigGroup = ['Wallpaper','org.kde.image','General'];
 desktop.writeConfig('Image', 'file:///usr/share/wallpapers/GITM/contents/images/1920x1080.svg');
}
