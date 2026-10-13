"""Explicit adapter capability registry; declarations never establish vehicle coverage."""
import re
from dataclasses import dataclass
from typing import Callable

@dataclass(frozen=True)
class Definition:
 id:str
 name:str
 transports:tuple
 protocols:tuple
 implementation:str
 verification:str
 scope:str
 factory:Callable|None=None

class Registry:
 def __init__(self):self.definitions={}
 def register(self,definition):
  if not isinstance(definition,Definition) or not re.fullmatch('[a-z][a-z0-9_-]{1,40}',definition.id):raise ValueError('Invalid adapter definition')
  if definition.id in self.definitions:raise ValueError('Adapter already registered')
  if definition.implementation not in ('planned','implemented'):raise ValueError('Invalid implementation state')
  if definition.verification not in ('not_tested','simulator','bench','vehicle'):raise ValueError('Invalid verification state')
  if definition.factory is not None and not callable(definition.factory):raise ValueError('Callable connector factory required')
  self.definitions[definition.id]=definition
 def create(self,key):
  definition=self.definitions.get(key)
  if definition is None or definition.factory is None:raise ValueError('No executable connector registered for this adapter')
  connector=definition.factory()
  if any(not callable(getattr(connector,method,None)) for method in ('connect','query','info','close')):raise ValueError('Connector does not implement the unified command interface')
  return connector
 def catalog(self):
  return [{'id':d.id,'name':d.name,'transports':list(d.transports),'protocols':list(d.protocols),'implementation':d.implementation,'verification':d.verification,'scope':d.scope,'executable':d.factory is not None,'vehicle_coverage':'not established by registry'} for d in self.definitions.values()]

def shared_elm():
 import transport
 return transport.LINK

def default_registry():
 registry=Registry()
 registry.register(Definition('elm','ELM / STN',('usb','wifi','bluetooth','rfcomm','ble'),('OBD emissions',),'implemented','simulator','Existing ELM runtime; simulator tested over TCP only. Other transports and vehicle coverage not established.',shared_elm))
 for key,name,transports,protocols in [('socketcan','SocketCAN / USB-CAN',('socketcan',),('CAN',)),('pcan','PCAN',('usb',),('CAN',)),('kvaser','Kvaser',('usb',),('CAN',)),('vector','Vector',('vendor',),('CAN',)),('kline','K-Line',('serial',),('KWP2000','ISO9141')),('doip','DoIP',('ethernet',),('ISO13400',)),('j2534','J2534 Pass-Thru',('vendor',),('J2534',))]:
  registry.register(Definition(key,name,transports,protocols,'planned','not_tested','Unified OBD connector not integrated; raw CAN tooling, when available, is a separate function.'))
 return registry
