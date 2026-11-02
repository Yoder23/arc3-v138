"""Admit learned geometric goal coverage through initial legal pixels."""
from cross_alignment_learner_v20 import Agent as Cross
from cross_shape_geometry_v2 import scene

def route(raw):
    assert set(raw)=={'frame','state','available_actions','levels_completed'}
    if set(raw['available_actions'])=={1,2,3,4,5}:
        objects,targets=scene(raw)
        if 2<=len(objects)<=6 and sum(map(len,targets.values()))>=4 and all(o['radius']['kind'] in ('plus','diagonal','diamond','horizontal','vertical') for o in objects.values()):return 'cross'
    return 'parent'
class Controller:
    def __init__(self,parent):self.parent=parent;self.checked=False;self.route=None;self.expert=None
    def respond(self,raw):
        if not self.checked:
            self.checked=True;self.route=route(raw)
            if self.route=='cross':self.expert=Cross()
        return self.parent.respond(raw) if self.route=='parent' else self.expert.respond(raw)
