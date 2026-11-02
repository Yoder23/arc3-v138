"""Admit a learned terrain-switch specialist using visible structure only."""
from switch_bridge_inquiry_v25 import Agent as Bridge
from switch_bridge_inquiry_v25 import Agent as Detector

def route(raw):
 if not {1,2,3,4,6}.issubset(raw['available_actions']):return 'parent'
 a=Detector();a.find(raw)
 if not a.field:return 'parent'
 controls=[p for p in a.buttons if p['x']>=a.field['w']]
 return 'bridge' if len(a.markers)==2 and len({p['color']for p in a.markers})==2 and controls else 'parent'
class Controller:
 def __init__(self,parent):self.parent=parent;self.checked=False;self.route=None;self.expert=None
 def respond(self,raw):
  if not self.checked:
   self.checked=True;self.route=route(raw)
   if self.route=='bridge':self.expert=Bridge()
  return self.parent.respond(raw)if self.route=='parent'else self.expert.respond(raw)
