"""Admit relational group learning from visible endpoints, mean marker and dotted goals."""
from group_centroid_learner_v14 import Agent as Centroid,scene

def route(raw):
    assert set(raw)=={'frame','state','available_actions','levels_completed'}
    if set(raw['available_actions'])=={6}:
        ends,centers,goals=scene(raw)
        if len(ends)>=2 and goals and any(len([o for o in ends if o['group']==g])>=2 and tuple(sum(o['point'][i] for o in ends if o['group']==g)//len([o for o in ends if o['group']==g]) for i in (0,1))==p for g,p in centers.items()):return 'centroid'
    return 'parent'
class Controller:
    def __init__(self,parent):self.parent=parent;self.checked=False;self.route=None;self.expert=None
    def respond(self,raw):
        if not self.checked:
            self.checked=True;self.route=route(raw)
            if self.route=='centroid':self.expert=Centroid()
        return self.parent.respond(raw) if self.route=='parent' else self.expert.respond(raw)
