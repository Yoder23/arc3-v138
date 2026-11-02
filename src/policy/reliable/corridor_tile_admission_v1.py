"""Observable admission for a lateral body among repeated removable tiles."""
from collections import Counter
from structured_interaction_probe_v1 import parts
from residual_tile_inquiry_v1 import Agent as Expert
def route(o):
 if not {3,4,6}.issubset(o['available_actions']):return 'parent'
 ps=parts(o['frame'])
 bodies=[p for p in ps if 8<=p['y']<60 and 3<=p['area']<=12 and 1<=p['w']<p['h']<=5]
 groups=Counter((p['h'],p['w'],p['shape']) for p in ps if 3<=p['h']<=7 and p['h']==p['w'] and p['area']>=16)
 return 'corridor' if len(bodies)==1 and max(groups.values(),default=0)>=4 else 'parent'
class Controller:
 def __init__(self,parent):self.parent=parent;self.route=None;self.expert=None
 def respond(self,o):
  if self.route is None:
   self.route=route(o)
   if self.route=='corridor':self.expert=Expert()
  return self.expert.respond(o) if self.route=='corridor' else self.parent.respond(o)
