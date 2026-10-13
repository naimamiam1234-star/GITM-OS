"""Decode the original 24-fps MP4 clips with Qt/FFmpeg; no frame slideshow."""
from pathlib import Path
from PySide6.QtCore import Qt,QTimer,QUrl
from PySide6.QtWidgets import QWidget,QVBoxLayout,QLabel
from PySide6.QtMultimedia import QMediaPlayer,QVideoSink
from PySide6.QtGui import QPixmap
class Intro(QWidget):
 def __init__(self,done,mode='dark'):
  from branding import session_clip
  clip=session_clip(mode)
  super().__init__();self.done=done;self.finished=False;self.index=0;self.clips=[clip] if clip else []
  self.setWindowFlags(Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint);self.setStyleSheet('background:#020b14');layout=QVBoxLayout(self);layout.setContentsMargins(0,0,0,0);self.video=QLabel();self.video.setAlignment(Qt.AlignCenter);layout.addWidget(self.video);self.sink=QVideoSink(self);self.sink.videoFrameChanged.connect(self.frame);self.player=QMediaPlayer(self);self.player.setVideoSink(self.sink);self.player.mediaStatusChanged.connect(self.status);self.player.errorOccurred.connect(lambda *a:self.finish());self.guard=QTimer(self);self.guard.setSingleShot(True);self.guard.timeout.connect(self.finish)
 def frame(self,frame):
  if frame.isValid():
   image=frame.toImage()
   if not image.isNull():self.video.setPixmap(QPixmap.fromImage(image).scaled(self.video.size(),Qt.KeepAspectRatio,Qt.SmoothTransformation))
 def start(self):
  self.showFullScreen();self.guard.start(14000);self.next()
 def next(self):
  if self.index>=len(self.clips):self.finish();return
  clip=self.clips[self.index];self.index+=1
  if not clip.is_file():self.finish();return
  self.player.setSource(QUrl.fromLocalFile(str(clip)));self.player.play()
 def status(self,s):
  if s==QMediaPlayer.MediaStatus.EndOfMedia:self.next()
 def finish(self):
  if self.finished:return
  self.finished=True;self.guard.stop();self.player.stop();self.hide();self.done();self.deleteLater()
 def keyPressEvent(self,e):
  if e.key() in (Qt.Key_Escape,Qt.Key_Space):self.finish()
  else:super().keyPressEvent(e)

if __name__=='__main__':
 import sys
 from PySide6.QtWidgets import QApplication
 app=QApplication(sys.argv);view=Intro(app.quit);view.start();sys.exit(app.exec())
