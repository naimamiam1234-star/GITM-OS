"""Shared native diagnostic design components. No adapter/network I/O."""
from pathlib import Path
import unicodedata
from PySide6.QtCore import Qt,QSize,QByteArray,QObject,QEvent,QItemSelectionModel
from PySide6.QtGui import QIcon,QPixmap,QPainter
from PySide6.QtWidgets import QFrame,QVBoxLayout,QLabel,QPushButton,QTableWidget,QStyledItemDelegate
from i18n import language

TRANSLATIONS={}
def header_icon(kind,color="#ecf3fa"):
 paths={'menu':'<path d="M4 6h16M4 12h16M4 18h16"/>','appearance':'<circle cx="12" cy="12" r="8"/><path d="M12 4a8 8 0 0 1 0 16Z" fill="#ecf3fa"/>','split':'<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M12 5v14"/>','notifications':'<path d="M5 17h14l-2-3V9a5 5 0 0 0-10 0v5Zm5 3h4"/>'}
 from PySide6.QtSvg import QSvgRenderer
 svg='<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><g fill="none" stroke="#ecf3fa" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'+paths[kind]+'</g></svg>'
 svg=svg.replace('#ecf3fa',color)
 pix=QPixmap(24,24);pix.fill(Qt.transparent);painter=QPainter(pix);QSvgRenderer(QByteArray(svg.encode())).render(painter);painter.end();return QIcon(pix)
def triple(ar,fr,en):
 values=(ar,fr,en)
 for text in values:TRANSLATIONS[text]=values
 return values[{'ar':0,'fr':1,'en':2}.get(language(),2)]
def palette(dark=False):
 return {'background':'#0e171e' if dark else '#f3f5f7','surface':'#18232c' if dark else '#ffffff','text':'#ecf3fa' if dark else '#163249','muted':'#b1c1d0' if dark else '#4c657b','outline':'#33485e' if dark else '#d4dfe9','primary':'#f2b632' if dark else '#b56500','on_primary':'#101820' if dark else '#ffffff','warning':'#a43c14' if not dark else '#b95522','success':'#138158','header':'#111e28' if dark else '#e8edf2','selection':'#264f66' if dark else '#d9edf7','header_surface':'#182b3d' if dark else '#ffffff','header_text':'#ecf3fa' if dark else '#163249'}
def styles(dark=False,font_size=16):
 p=palette(dark);size=max(16,min(22,int(font_size)))
 return f'''QWidget{{font-family:Tajawal,"Noto Sans Arabic",sans-serif;font-size:{size}px;background:{p['background']};color:{p['text']}}}
 QLabel{{background:transparent}} QLabel#brand{{font-size:20px;font-weight:600;color:{p['primary']}}} QLabel#pageTitle{{font-size:18px;font-weight:600;color:{p['header_text']}}} QLabel#heading{{font-size:20px;font-weight:600}} QLabel#cardTitle{{font-weight:600}} QLabel#metricValue{{font-size:23px;font-weight:600}} QLabel#muted{{color:{p['muted']}}}
 QFrame#infoCard,QFrame#metricCard,QFrame#toolCard{{background:{p['surface']};border:1px solid {p['outline']};border-radius:12px}} QFrame#infoCard QLabel,QFrame#metricCard QLabel{{background:transparent}} QWidget#footer,QWidget#sidebar{{background:{p['header']};color:white}} #footer QLabel,#sidebar QLabel{{color:{p['text']}}} QWidget#header{{background:{p['header_surface']};border-bottom:1px solid {p['outline']}}} #header QLabel{{color:{p['header_text']}}} #header QLineEdit,#header QComboBox{{background:{p['background']};color:{p['text']};border-color:{p['outline']}}} #header QPushButton{{background:{p['surface']};color:{p['text']};border-color:{p['outline']}}} #sidebar QPushButton{{background:transparent;color:{p['text']};text-align:left;padding:10px;border:0;border-radius:8px}} #sidebar QPushButton:hover{{background:#25485d}}
 QPushButton{{background:{p['surface']};color:{p['text']};border:1px solid {p['outline']};border-radius:8px;padding:8px 12px;min-height:24px}} QPushButton:hover{{border-color:#0084ac;background:{p['selection']}}} QPushButton[role="primary"]{{background:{p['primary']};color:{p['on_primary']};border-color:{p['primary']}}} QPushButton[role="warning"]{{background:{p['warning']};color:white;border-color:{p['warning']}}} QPushButton:disabled{{background:{p['background']};color:{p['muted']};border-color:{p['outline']}}}
 QWidget#assistantPanel{{background:{p['surface']};border-left:1px solid {p['outline']}}} QLabel#sessionIdentity{{background:{p['selection']};color:{p['text']};padding:10px;border-radius:8px}} QPushButton#sessionAssistantButton{{background:{p['primary']};color:{p['on_primary']};border-color:{p['primary']}}}
 QPushButton#vehicleBrand{{min-height:72px}} QPushButton#vehicleBrand:checked{{background:{p['selection']};border:2px solid {p['primary']}}}
 QPushButton:focus,QLineEdit:focus,QComboBox:focus,QTextEdit:focus,QTableWidget:focus{{border:2px solid #22a9cf}} QPushButton#card{{background:{p['surface']};color:{p['text']};padding:5px;border-radius:12px}} QLabel#cardlabel{{font-size:{size}px;font-weight:500}}
 QLineEdit,QComboBox,QSpinBox,QDoubleSpinBox,QTextEdit,QPlainTextEdit,QTableWidget,QTreeWidget,QListWidget{{background:{p['surface']};color:{p['text']};border:1px solid {p['outline']};border-radius:8px;padding:6px;selection-background-color:{p['selection']};selection-color:{p['text']}}} QHeaderView::section{{background:{p['background']};color:{p['text']};padding:7px;border:0;border-bottom:1px solid {p['outline']}}} QTableCornerButton::section{{background:{p['background']}}} QTabWidget::pane{{border:1px solid {p['outline']};border-radius:8px}} QTabBar::tab{{background:{p['background']};padding:8px 12px;border:1px solid {p['outline']}}} QTabBar::tab:selected{{background:{p['surface']};border-bottom:2px solid {p['primary']}}}
 QProgressBar{{background:{p['surface']};border:1px solid {p['outline']};border-radius:7px;min-height:18px;text-align:center}} QProgressBar::chunk{{background:{p['primary']};border-radius:7px}} QScrollArea{{border:0}} QMenu{{background:{p['surface']};color:{p['text']};border:1px solid {p['outline']};padding:5px}} QMenu::item{{padding:8px 18px}} QMenu::item:selected{{background:{p['selection']}}} QToolTip{{background:{p['header']};color:white;border:1px solid {p['outline']};padding:6px}} QSplitter::handle{{background:{p['outline']}}}'''
class InfoCard(QFrame):
 def __init__(self,title,parent=None):
  super().__init__(parent);self.setObjectName('infoCard');self.body=QVBoxLayout(self);self.body.setContentsMargins(14,10,14,10);self.body.setSpacing(7);self.title_label=QLabel(title);self.title_label.setWordWrap(True);self.title_label.setObjectName('cardTitle');self.body.addWidget(self.title_label)
class MetricCard(InfoCard):
 def __init__(self,title,value='—',detail='',parent=None):
  super().__init__(title,parent);self.setObjectName('metricCard');self.value_label=QLabel(str(value));self.value_label.setObjectName('metricValue');self.detail_label=QLabel(str(detail));self.detail_label.setObjectName('muted');self.detail_label.setWordWrap(True);self.body.addWidget(self.value_label);self.body.addWidget(self.detail_label);self.setMinimumWidth(90)
 def set_value(self,value,detail=None):
  self.value_label.setText('—' if value is None else str(value))
  if detail is not None:self.detail_label.setText(str(detail))
def icon(name):
 paths={
 'home':'<path d="m3 10 9-7 9 7v11h-6v-7H9v7H3Z"/>',
 'car':'<path d="m4 10 2-6h12l2 6v9H4Z M4 10h16 M7 14h2 M15 14h2"/>',
 'smart':'<circle cx="10" cy="10" r="6"/><path d="m15 15 6 6 M7 10h6 M10 7v6"/>',
 'engine':'<path d="M4 8h12l4 4v7H4Z M8 4h8 M12 4v4 M1 11v5 M20 11h3v8h-3"/>',
 'tools':'<path d="M14 3a6 6 0 0 0-6 8L2 17l5 5 6-6a6 6 0 0 0 8-6l-4 3-5-5Z"/>',
 'data':'<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 4 16 4 16 0V5 M4 12c0 4 16 4 16 0"/>',
 'history':'<circle cx="12" cy="12" r="9"/><path d="M12 6v6l4 3"/>',
 'settings':'<path d="M4 5h16 M4 12h16 M4 19h16 M8 2v6 M16 9v6 M9 16v6"/>',
 'ai':'<path d="m12 2 3 7 7 3-7 3-3 7-3-7-7-3 7-3Z"/>',
 'reports':'<path d="M5 2h10l4 4v16H5Z M15 2v5h4 M8 11h8 M8 15h8 M8 19h5"/>',
 'live':'<path d="M2 12h5l3-8 4 16 3-8h5"/>'}
 if name in paths:
  from PySide6.QtSvg import QSvgRenderer
  svg='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g fill="none" stroke="#27a7c7" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'+paths[name]+'</g></svg>'
  pix=QPixmap(32,32);pix.fill(Qt.transparent);painter=QPainter(pix);QSvgRenderer(QByteArray(svg.encode())).render(painter);painter.end();return QIcon(pix)
 root=Path(__file__).parent/'assets'
 for folder in ('tools','desktop'):
  p=root/folder/(name+'.svg')
  if p.exists():return QIcon(str(p))
 return QIcon.fromTheme(name)
def action_button(text,role='secondary',icon=None):
 b=QPushButton(text);b.setProperty('role',role);b.setMinimumHeight(44);b.setAccessibleName(text)
 if icon is not None:b.setIcon(icon if isinstance(icon,QIcon) else globals()['icon'](icon));b.setIconSize(QSize(22,22))
 return b
class ReadableCells(QStyledItemDelegate):
 def initStyleOption(self,option,index):
  super().initStyleOption(option,index)
  rtl=any(unicodedata.bidirectional(char) in ('R','AL') for char in option.text)
  option.direction=Qt.RightToLeft if rtl else Qt.LeftToRight
  option.displayAlignment=(Qt.AlignRight if rtl else Qt.AlignLeft)|Qt.AlignVCenter

class TableReadability(QObject):
 def __init__(self,table):
  super().__init__(table);self.table=table;table.installEventFilter(self);self.resize_rows()
 def resize_rows(self):
  self.table.verticalHeader().setDefaultSectionSize(max(34,self.table.fontMetrics().height()+16))
 def eventFilter(self,obj,event):
  if event.type() in (QEvent.FontChange,QEvent.StyleChange,QEvent.Show):self.resize_rows()
  return False

def select_table_row(table,row):
 # Qt's RTL selectRow geometry path can return no selection. Select the model
 # row directly, retaining native selection signals and selectedItems().
 if table.layoutDirection()!=Qt.RightToLeft:
  return QTableWidget.selectRow(table,row)
 if 0<=row<table.rowCount() and table.columnCount():
  index=table.model().index(row,0)
  table.selectionModel().setCurrentIndex(index,QItemSelectionModel.NoUpdate)
  table.selectionModel().select(index,QItemSelectionModel.ClearAndSelect|QItemSelectionModel.Rows)

def configure_table(table):
 table.setEditTriggers(QTableWidget.NoEditTriggers);table.setAlternatingRowColors(False);table.setSelectionBehavior(QTableWidget.SelectRows);table.horizontalHeader().setStretchLastSection(True);table.verticalHeader().hide();table.setSortingEnabled(False);table.setItemDelegate(ReadableCells(table));table._readability=TableReadability(table);table.selectRow=lambda row:select_table_row(table,row)
