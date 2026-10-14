"""Original schematic artwork, explicitly generic rather than a model photograph."""
from PySide6.QtCore import Qt,QRectF
from PySide6.QtGui import QPainter,QPen,QColor,QLinearGradient,QPainterPath
from PySide6.QtWidgets import QWidget
class VehicleSilhouette(QWidget):
 def __init__(self,parent=None):
  super().__init__(parent);self.setStyleSheet('background:transparent');self.setMinimumSize(120,200);self.setMaximumWidth(210)
  self.setAccessibleName('Generic vehicle schematic — not a model photograph')
 def paintEvent(self,event):
  p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);p.translate(self.width()/2,self.height()/2);scale=min(self.width()/150,self.height()/270);p.scale(scale,scale)
  dark=self.palette().window().color().lightness()<128
  line=QColor('#748b9c' if dark else '#536c7d');p.setPen(QPen(line,1.8))
  for y in (-86,64):
   p.setBrush(QColor('#101820'));p.drawRoundedRect(QRectF(-53,y,14,36),5,5);p.drawRoundedRect(QRectF(39,y,14,36),5,5)
  body=QPainterPath();body.moveTo(-32,-122);body.cubicTo(-53,-110,-50,-65,-48,-30);body.lineTo(-48,76);body.cubicTo(-47,110,-38,122,0,124);body.cubicTo(38,122,47,110,48,76);body.lineTo(48,-30);body.cubicTo(50,-65,53,-110,32,-122);body.quadTo(0,-131,-32,-122)
  grad=QLinearGradient(-48,0,48,0);grad.setColorAt(0,QColor('#23313c'));grad.setColorAt(.48,QColor('#8495a0'));grad.setColorAt(1,QColor('#263742'));p.setBrush(grad);p.drawPath(body)
  p.setBrush(QColor('#14232e'));p.drawRoundedRect(QRectF(-32,-60,64,130),22,22)
  p.setBrush(QColor('#243f50'));p.drawRoundedRect(QRectF(-34,-79,68,37),12,12);p.drawRoundedRect(QRectF(-32,65,64,28),10,10)
  p.setPen(QPen(QColor('#39adc2'),2));p.drawLine(-36,-102,-17,-108);p.drawLine(17,-108,36,-102)
  p.setPen(QPen(QColor('#ce6a54'),2));p.drawLine(-34,106,-18,110);p.drawLine(18,110,34,106)
  p.end()
