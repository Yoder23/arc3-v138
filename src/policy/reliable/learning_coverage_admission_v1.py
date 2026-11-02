"""One-time visual admission to learned connector or coupled-motion experts."""
from connector_assembly_admission_v2 import route as connector_route
from connector_assembly_learner_v16 import Agent as Connector
from coupled_navigation_learner_v5 import Agent as Coupled,actors

def route(raw):
    assert set(raw)=={'frame','state','available_actions','levels_completed'}
    if connector_route(raw)=='connector':return 'connector'
    if raw['state']!='NOT_FINISHED' or not {1,2,3,4,5}<=set(raw['available_actions']):return 'parent'
    signature,pos=actors(raw['frame'])
    if not pos:return 'parent'
    color,size=signature;rings=[];f=raw['frame']
    for y,x in pos:
        ring={(y-1,x+b) for b in range(size)}|{(y+size,x+b) for b in range(size)}|{(y+a,x-1) for a in range(size)}|{(y+a,x+size) for a in range(size)}
        if any(not(0<=a<64 and 0<=b<64) for a,b in ring):return 'parent'
        values={f[a][b] for a,b in ring}
        if len(values)!=1 or color in values:return 'parent'
        rings.append(values)
    return 'coupled' if rings[0]==rings[1] else 'parent'
class Controller:
    def __init__(self,parent):self.parent=parent;self.checked=False;self.route=None;self.expert=None
    def respond(self,raw):
        if not self.checked:
            self.checked=True;self.route=route(raw)
            if self.route=='connector':self.expert=Connector()
            elif self.route=='coupled':self.expert=Coupled()
        return self.parent.respond(raw) if self.route=='parent' else self.expert.respond(raw)
