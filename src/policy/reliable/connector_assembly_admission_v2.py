"""One-time legal visual admission to the retained connector learner."""
from composite_connector_learner_v5 import objects,ports
from composite_connector_learner_v6 import hypotheses
from connector_assembly_learner_v7 import Agent as Expert

def route(raw):
    assert set(raw)=={'frame','state','available_actions','levels_completed'}
    if raw['state']!='NOT_FINISHED' or not {1,2,3,4,5,6}<=set(raw['available_actions']):return 'parent'
    scene=objects(raw['frame'])
    if len(scene)==2 and all(ports(o) for o in scene) and any(hypotheses(o,scene) for o in scene):return 'connector'
    return 'parent'
class Controller:
    def __init__(self,parent):self.parent=parent;self.checked=False;self.route=None;self.expert=None
    def respond(self,raw):
        if not self.checked:
            self.checked=True;self.route=route(raw)
            if self.route=='connector':self.expert=Expert()
        return self.parent.respond(raw) if self.route=='parent' else self.expert.respond(raw)
