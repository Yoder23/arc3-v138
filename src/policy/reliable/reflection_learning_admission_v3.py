"""Admit initial reflected silhouettes using visible shape relationships and controls."""
from modal_scene_v7 import objects,shape
from reflection_assignment_inquiry_v18 import Agent as Reflection

def route(raw):
 assert set(raw)=={'frame','state','available_actions','levels_completed'}
 if not {1,2,3,4,5,7}<=set(raw['available_actions']):return'parent'
 ps=[p for p in objects(raw)if p['h']<24 and p['w']<24]
 for b in ps:
  if sum(raw['frame'][b['y']+y][b['x']+x]!=b['color']for y,x in shape(b))<3:continue
  mirrors=[tuple(sorted((b['h']-1-y,x)for y,x in shape(b))),tuple(sorted((y,b['w']-1-x)for y,x in shape(b)))]
  for mirrored in mirrors:
   matches=[p for p in ps if p['color']!=b['color']and shape(p)==mirrored]
   if len({p['color']for p in matches})>=2:return'reflection'
 return'parent'
class Controller:
 def __init__(self,parent):self.parent=parent;self.checked=False;self.route=None;self.expert=None
 def respond(self,raw):
  if not self.checked:
   self.checked=True;self.route=route(raw)
   if self.route=='reflection':self.expert=Reflection()
  return self.parent.respond(raw)if self.route=='parent'else self.expert.respond(raw)
