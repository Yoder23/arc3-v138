"""Choose a specialist once from legal visual evidence; retain the parent policy."""
from matrix_admission_v1 import admissible as matrix_admissible
from matrix_conditional_program_v14 import Agent as Matrix
from selectable_multi_object_learner_v18 import Agent as Multi
from selectable_rect_geometry_v1 import actor_group,rings

def route(raw):
    assert set(raw)=={'frame','state','available_actions','levels_completed'}
    if matrix_admissible(raw):return 'matrix'
    if raw['state']=='NOT_FINISHED' and {1,2,3,4,6}<=set(raw['available_actions']):
        bodies=actor_group(raw['frame'])
        goals=[g for g in rings(raw['frame']) if bodies and g['ink']!=bodies[0]['ink'] and any(tuple(g['box'][2:])==(b['box'][2]+2,b['box'][3]+2) for b in bodies)]
        if 2<=len(goals)<=len(bodies)<=4:return 'multi'
    return 'parent'

class Controller:
    def __init__(self,parent):self.parent=parent;self.checked=False;self.route=None;self.expert=None
    def respond(self,raw):
        if not self.checked:
            self.checked=True;self.route=route(raw)
            if self.route=='matrix':self.expert=Matrix()
            elif self.route=='multi':self.expert=Multi()
        return self.parent.respond(raw) if self.route=='parent' else self.expert.respond(raw)
