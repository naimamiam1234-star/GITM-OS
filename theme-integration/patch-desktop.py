"""Replace parallel settings surfaces with the native single-instance application."""
from pathlib import Path
import sys
p=Path(sys.argv[1]);s=p.read_text()
start=s.index(' def settings(self):');end=s.index(' def system_information(self):',start)
s=s[:start]+''' def settings(self):
  self.control.hide();self.status_buttons['chevron'].setChecked(False)
  self.launch('settings',['systemsettings'])
'''+s[end:]
start=s.index(' def choose_appearance(self):');end=s.index(' def toggle_airplane(self):',start)
s=s[:start]+''' def choose_appearance(self):
  self.launch('settings',['systemsettings','kcm_colors'])
'''+s[end:]
s=s.replace(" def launch(self,key,argv):\n", " def launch(self,key,argv):\n  if argv[0]=='systemsettings':key='settings'\n")
s=s.replace("p.setProcessEnvironment(env);p.setProgram(argv[0]);", "env.insert('LANG','ar_MA.UTF-8') if argv[0]=='systemsettings' else None\n  p.setProcessEnvironment(env);p.setProgram(argv[0]);")
s=s.replace("  tip=QLabel('مساحة عمل جاهزة\\nافتح ملفاتك وبرامجك، وانتقل إلى AutoDiag عند بدء فحص السيارة.');tip.setWordWrap(True);tip.setStyleSheet('font-size:16px;color:#bfcee1');right.addWidget(tip)\n",'')
s=s.replace("QPushButton(label);b.setIcon(self.icon(icon));", "QPushButton(label);b.setIcon(self.icon(icon));")
s=s.replace("('الصوت','volume','sound',['pavucontrol'])", "('الصوت','volume','sound',['systemsettings','kcm_pulseaudio'])")
s=s.replace("('الشاشة','display','display',['systemsettings'])", "('الشاشة','display','display',['systemsettings','kcm_kscreen'])")
s=s.replace("('الطاقة','battery','power-settings',['systemsettings'])", "('الطاقة','battery','power-settings',['systemsettings','kcm_powerdevilprofilesconfig'])")
s=s.replace("المساحة المتاحة  {m['disk_free']/g:.1f} GB · RAM {m['ram_total']/g:.1f} GB", "التخزين المتاح: \\u2066{m['disk_free']/g:.1f} GB\\u2069\\nRAM: \\u2066{m['ram_total']/g:.1f} GB\\u2069")
s=s.replace(" d=QDialog(self);d.setWindowTitle(title);", " d=QDialog(self);d.setWindowIcon(self.icon('settings'));d.setWindowTitle(title);")
# Set the desktop's own WM_CLASS/icon instead of the generic Python/X icon.
s=s.replace("  self.setLayoutDirection(Qt.LeftToRight);self.setStyleSheet(STYLE)", "  self.setWindowIcon(self.icon('settings'))\n  QApplication.setDesktopFileName('gitm-desktop')\n  self.setLayoutDirection(Qt.LeftToRight);self.setStyleSheet(STYLE)")
# Propagate custom light/dark changes through KDE's supported colour-scheme tool.
needle=" def apply_appearance(self):\n"
s=s.replace(needle,needle+"  mode=self.appearance['mode']\n  if getattr(self,'_native_mode',None)!=mode and shutil.which('plasma-apply-colorscheme'):\n   self._native_mode=mode\n   QProcess.startDetached('plasma-apply-colorscheme',['BreezeLight' if mode=='light' else 'BreezeDark'])\n")
p.write_text(s)
compile(s,str(p),'exec')
