"""One-time legal-pixel admission to retained paint composition."""
from stencil_composition_inquiry_v4 import Agent as Stencil
from structured_interaction_probe_v1 import parts
def route(raw):
 assert set(raw)=={'frame','state','available_actions','levels_completed'}
 if set(raw['available_actions'])!={1,2,3,4,5,6}:return 'parent'
 ps=parts(raw['frame']);pieces=[p for p in ps if p['x']<16 and p['y']<16 and p['area']>=9]
 if len(pieces)<2:return 'parent'
 y=min(p['y'] for p in pieces);x=min(p['x'] for p in pieces);h=max(p['y']+p['h'] for p in pieces)-y;w=max(p['x']+p['w'] for p in pieces)-x
 canvases=[p for p in ps if p['y']>=16 and p['h']==h and p['w']==w and p['area']==h*w];tools=[p for p in ps if p['y']>=16 and (p['h'],p['w'],p['area']) in [(9,14,30),(14,9,30),(17,17,43)]]
 return 'stencil' if len(canvases)==len(tools)==1 else 'parent'
class Controller:
    def __init__(self,parent):self.parent=parent;self.checked=False;self.route=None;self.expert=None
    def respond(self,raw):
        if not self.checked:
            self.checked=True;self.route=route(raw)
            if self.route=='stencil':self.expert=Stencil()
        return self.parent.respond(raw) if self.route=='parent' else self.expert.respond(raw)
