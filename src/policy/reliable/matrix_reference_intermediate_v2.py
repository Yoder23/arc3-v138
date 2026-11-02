"""Offer a reference-linked interaction before unrelated intermediate experiments."""
from matrix_intermediate_learner_v4 import Agent as Base
from matrix_reference_cues_v1 import cues
from matrix_motion_learner_v6 import objects
from matrix_intermediate_learner_v3 import gap
class Agent(Base):
    def issue(self,raw,action,data,phase,route=None,extra=None):
        ink={c['ink'] for c in cues(raw,self.grid)}
        targets=[o for o in objects(raw['frame'],[self.grid['box']]) if not o.get('parts') and o['ink'] in ink and gap(o['box'],self.grid['box'])>12]
        if not hasattr(self,'executed_intermediate_keys'):self.executed_intermediate_keys=set()
        key=(tuple(self.experiment['landmark']['box']),self.experiment['landmark']['ink']) if self.experiment else None
        if phase not in ('goal_route','motion_inquiry') and targets:
            if key and key not in self.executed_intermediate_keys:self.attempted.discard(key)
            self.experiment=None
            return dict(done=True,action=None,data={})
        if key:self.executed_intermediate_keys.add(key)
        return super().issue(raw,action,data,phase,route,extra)
