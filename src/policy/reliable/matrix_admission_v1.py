"""One-time pixel admission for input-grid plus independently visible body and goal."""
from matrix_intermediate_learner_v4 import Agent
from matrix_motion_learner_v6 import grids,objects

def admissible(raw):
    if raw['state']!='NOT_FINISHED' or not set((1,2,3,4,6)).issubset(raw['available_actions']):return False
    found=grids(raw['frame'])
    if not found:return False
    obs=objects(raw['frame'],[found[0]['box']])
    for body in obs:
        if not body.get('parts'):continue
        goals=[g for g in obs if not g.get('parts') and g['ink'] in body['ink'] and len(g['shape'])==g['box'][2]*g['box'][3] and g['box'][2]==g['box'][3]]
        if goals:return True
    return False

class Controller:
    def __init__(self,parent):
        self.parent=parent;self.checked=False;self.admitted=False;self.expert=None
    def respond(self,raw):
        if not self.checked:
            self.checked=True;self.admitted=admissible(raw)
            if self.admitted:self.expert=Agent()
        return self.expert.respond(raw) if self.admitted else self.parent.respond(raw)
