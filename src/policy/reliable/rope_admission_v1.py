"""One-time admission from the visible rope head and sequence legend."""
from rope_rail_composer_v5 import Agent as Rope
from rope_physics_model_v2 import scene
from structured_interaction_probe_v1 import parts
def route(raw):
 assert set(raw)=={'frame','state','available_actions','levels_completed'}
 if set(raw['available_actions'])!={1,2,3,4,6,7}:return 'parent'
 c=scene(raw)
 if not c:return 'parent'
 ps=parts(raw['frame']);legends=[p for p in ps if p['y']>=54 and p['h']==p['w']==6 and p['area']==18 and p['color']==c['head']['color']];items=[p for p in ps if p['y']>=54 and p['h']==p['w']==4 and p['area']==16]
 return 'rope' if len(legends)==1 and items else 'parent'
class Controller:
 def __init__(self,parent):self.parent=parent;self.checked=False;self.route=None;self.expert=None
 def respond(self,raw):
  if not self.checked:
   self.checked=True;self.route=route(raw)
   if self.route=='rope':self.expert=Rope()
  return self.parent.respond(raw) if self.route=='parent' else self.expert.respond(raw)
