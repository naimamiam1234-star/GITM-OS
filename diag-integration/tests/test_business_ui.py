import unittest,tempfile,json
from pathlib import Path
from unittest.mock import patch
import store
from business_workspace import database,calculate,save_customer,remove_customer,save_invoice
class BusinessTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.patch=patch.object(store,'BASE',Path(self.tmp.name));self.patch.start()
 def tearDown(self):self.patch.stop();self.tmp.cleanup()
 def test_rounding_discount_tax(self):
  self.assertEqual(calculate([{'qty':'3','price':'0.335'}],'.01','10'),{'subtotal':'1.01','discount':'0.01','net':'1.00','tax_rate':'10','tax':'0.10','total':'1.10'})
  with self.assertRaises(ValueError):calculate([{'qty':'1','price':'2'}],'3','0')
 def test_schema_preserves_legacy(self):
  import workshop_tools
  with workshop_tools.database() as c:
   c.execute("INSERT INTO customers(name,phone,vehicle) VALUES('Legacy','1','Ford')")
   c.execute("INSERT INTO invoices(date,customer_id,customer,lines,total,currency) VALUES('2020-01-01',1,'{}','[]','10','MAD')")
  for n in range(2):
   with database() as c:
    self.assertEqual(c.execute('SELECT name,vehicle FROM customers').fetchone(),('Legacy','Ford'));self.assertEqual(c.execute('SELECT total,status FROM invoices').fetchone(),('10','unknown'))
 def test_soft_delete_retains_snapshot_and_draft(self):
  id=save_customer(None,{'name':'Original','vehicles':[{'make':'Ford','vin':'manual'}]})
  invoice=save_invoice(id,{'make':'Ford'},[{'description':'Inspection','category':'labor','qty':'1','price':'10'}])
  save_customer(id,{'name':'Changed','vehicles':[]});remove_customer(id)
  with database() as c:
   row=c.execute('SELECT customer,status FROM invoices WHERE id=?',(invoice,)).fetchone();self.assertEqual(json.loads(row[0])['name'],'Original');self.assertEqual(row[1],'draft');self.assertEqual(c.execute('SELECT deleted FROM customers WHERE id=?',(id,)).fetchone()[0],1)
 def test_backup_private_permissions(self):
  from business_workspace import private_json
  path=Path(self.tmp.name)/'backup.json';path.write_text('old');path.chmod(0o644);private_json(path,{'private':'customer'})
  self.assertEqual(path.stat().st_mode&0o777,0o600);self.assertEqual(json.loads(path.read_text()),{'private':'customer'})

from PySide6.QtWidgets import QApplication,QWidget
from business_workspace import Customers,InvoiceEditor,InvoiceHistory
class BusinessQtTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
 def test_empty_and_real_customer_invoice_views(self):
  with tempfile.TemporaryDirectory() as directory,patch.object(store,'BASE',Path(directory)):
   window=QWidget();uis=[]
   for typ in (Customers,InvoiceEditor,InvoiceHistory):uis.append(typ(window));self.assertEqual(uis[-1].table.rowCount(),1 if typ is InvoiceEditor else 0)
   customer=save_customer(None,{'name':'Workshop customer','vehicles':[{'make':'Ford','model':'Focus'}]})
   ui=InvoiceEditor(window);uis.append(ui);self.assertEqual(ui.customer.currentData()['id'],customer);self.assertEqual(ui.vehicle.currentData()['model'],'Focus');self.assertEqual(ui.status.currentData(),'draft');self.assertEqual(ui.tax.text(),'0')
   for widget in uis:widget.deleteLater()
   window.deleteLater();self.app.processEvents()
