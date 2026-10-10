// GITM bottom dock: application controls only. Status belongs at the top.
for (var old of panels()) { old.remove(); }
var dock = new Panel;
dock.location = 'bottom';
dock.height = 64;
dock.floating = true;
dock.alignment = 'center';
dock.lengthMode = 'fit';
dock.hiding = 'autohide';
var launcher = dock.addWidget('org.kde.plasma.kickoff');
launcher.currentConfigGroup = ['General'];
launcher.writeConfig('icon', '/usr/share/icons/hicolor/scalable/apps/gitm-more.svg');
var tasks = dock.addWidget('org.kde.plasma.icontasks');
tasks.currentConfigGroup = ['General'];
tasks.writeConfig('launchers', ['applications:gitm-autodiag.desktop','applications:org.kde.dolphin.desktop','applications:org.kde.falkon.desktop','applications:org.kde.kcalc.desktop','applications:systemsettings.desktop']);
tasks.writeConfig('showToolTips', true);
dock.addWidget('luisbocanegra.panel.colorizer');
