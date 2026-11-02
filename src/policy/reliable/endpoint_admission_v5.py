"""Admit a click-only scene when paired controls, rod endpoints and matching goal crosses agree."""
from hub_rod_inquiry_v2 import Agent as Endpoint
from endpoint_extension_inquiry_v2 import scene
def route(raw):
 assert set(raw)=={'frame','state','available_actions','levels_completed'}
 if raw['available_actions']!=[6]:return 'parent'
 bars,goals=scene(raw)
 return 'endpoint' if len(bars)==2 and len(goals)==2 and all(len(b['buttons'])==2 for b in bars) and len({b['marker'] for b in bars})==1 else 'parent'
class Controller:
 def __init__(self,parent):self.parent=parent;self.checked=False;self.route=None;self.expert=None
 def respond(self,raw):
  if not self.checked:
   self.checked=True;self.route=route(raw)
   if self.route=='endpoint':self.expert=Endpoint()
  return self.parent.respond(raw) if self.route=='parent' else self.expert.respond(raw)
