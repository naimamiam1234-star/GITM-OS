"""One user-local app, with allow-listed UI requests through a local SQLite queue."""
import sqlite3
from PySide6.QtCore import QLockFile,QObject,QTimer
TOOLS={'customers':'customers','invoice':'invoices','camera':'camera','pdf':'pdf','music':'media','update':'updates'}
def requested_tool(argv):
 try:value=argv[argv.index('--tool')+1]
 except (ValueError,IndexError):return ''
 return value if value in TOOLS else ''
def dispatch_existing_tool(window,argv):
 value=requested_tool(argv)
 if value:
  import workshop_tools
  getattr(workshop_tools,TOOLS[value])(window)

class InstanceGate(QObject):
 def __init__(self,state,parent=None):
  super().__init__(parent);state.mkdir(parents=True,exist_ok=True)
  self.lock=QLockFile(str(state/'autodiag-instance.lock'));self.path=state/'launch-requests.db'
  self.callback=None;self.owner=False;self.timer=QTimer(self);self.timer.setInterval(150);self.timer.timeout.connect(self.poll)
  with self.db() as db:
   db.execute("CREATE TABLE IF NOT EXISTS requests(id INTEGER PRIMARY KEY, assistant INTEGER NOT NULL, tool TEXT NOT NULL DEFAULT '')")
   if 'tool' not in {row[1] for row in db.execute('PRAGMA table_info(requests)')}:db.execute("ALTER TABLE requests ADD COLUMN tool TEXT NOT NULL DEFAULT ''")
  self.path.chmod(0o600)
 def db(self):return sqlite3.connect(self.path,timeout=.2)
 def acquire(self,argv,callback):
  if not self.lock.tryLock(0):
   with self.db() as db:db.execute('INSERT INTO requests(assistant,tool) VALUES(?,?)',(int('--assistant' in argv),requested_tool(argv)))
   return False
  self.owner=True;self.callback=callback
  self.timer.start();return True
 def poll(self):
  if not self.owner:return
  try:
   with self.db() as db:
    db.execute('BEGIN IMMEDIATE');rows=db.execute('SELECT id,assistant,tool FROM requests ORDER BY id LIMIT 32').fetchall()
    db.executemany('DELETE FROM requests WHERE id=?',[(row[0],) for row in rows])
  except sqlite3.OperationalError:return
  for _,assistant,tool in rows:self.callback((['--assistant'] if assistant==1 else [])+(['--tool',tool] if tool in TOOLS else []))
 def close(self):
  if self.owner:self.timer.stop();self.lock.unlock();self.owner=False
