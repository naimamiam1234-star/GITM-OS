// Use the same wallpaper for Plasma and the GITM workspace.
for (var desktop of desktops()) {
  desktop.wallpaperPlugin = 'org.kde.image';
  desktop.currentConfigGroup = ['Wallpaper', 'org.kde.image', 'General'];
  desktop.writeConfig('Image', 'file:///opt/gitm/assets/desktop/wallpaper.png');
  desktop.writeConfig('FillMode', 2);
}
// GITM bottom dock: application controls only. Status belongs at the top.
for (var old of panels()) { old.remove(); }
var dock = new Panel;
dock.location = 'bottom';
dock.height = 64;
dock.floating = true;
dock.alignment = 'center';
dock.lengthMode = 'fit';
dock.hiding = 'none'; // Automatic hiding remains available through native panel settings.
var launcher = dock.addWidget('org.kde.plasma.kickoff');
launcher.currentConfigGroup = ['General'];
launcher.writeConfig('icon', '/usr/share/icons/hicolor/scalable/apps/gitm-more.svg');
var tasks = dock.addWidget('org.kde.plasma.icontasks');
tasks.currentConfigGroup = ['General'];
tasks.writeConfig('launchers', ['applications:gitm-autodiag.desktop','applications:org.kde.dolphin.desktop','applications:org.kde.falkon.desktop','applications:org.kde.kcalc.desktop','applications:systemsettings.desktop']);
tasks.writeConfig('showToolTips', true);
var colorizer = dock.addWidget('luisbocanegra.panel.colorizer');
colorizer.currentConfigGroup = ['General'];
colorizer.writeConfig('hideWidget', true);
colorizer.writeConfig('globalSettings', "{\"panel\": {\"normal\": {\"enabled\": true, \"blurBehind\": true, \"radius\": {\"enabled\": true, \"corner\": {\"topLeft\": 22, \"topRight\": 22, \"bottomLeft\": 22, \"bottomRight\": 22}}, \"backgroundColor\": {\"enabled\": true, \"sourceType\": 1, \"systemColor\": \"backgroundColor\", \"systemColorSet\": \"Window\", \"alpha\": 0.92}, \"margin\": {\"enabled\": true, \"side\": {\"left\": 4, \"right\": 4, \"top\": 4, \"bottom\": 4}}, \"padding\": {\"enabled\": true, \"side\": {\"left\": 10, \"right\": 10, \"top\": 4, \"bottom\": 4}}}}, \"nativePanel\": {\"background\": {\"enabled\": true, \"opacity\": 0, \"shadow\": false}, \"floatingDialogs\": false, \"floatingDialogsAllowOverride\": false}}");
