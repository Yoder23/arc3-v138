"""Use an input-side reference to schedule a promising interaction before a direct-goal detour."""
from matrix_reference_intermediate_v2 import Agent as Base
from matrix_reference_cues_v1 import cues
from matrix_motion_learner_v6 import objects
from matrix_intermediate_learner_v3 import gap
class Agent(Base):
    def reference_targets(self,raw):
        if not self.grid or not self.moving:return []
        ink={c['ink'] for c in cues(raw,self.grid)}
        return [o for o in objects(raw['frame'],[self.grid['box']]) if not o.get('parts') and o['ink'] in ink and gap(o['box'],self.grid['box'])>12]
    def answer(self,raw,action,data,tag,extra=None):
        if tag in ('move_toward_visual_goal','conditional_motion_inquiry') and self.reference_targets(raw) and self.heading_witness:
            unknown=[a for a in raw['available_actions'] if a not in (0,6,7) and a not in self.orientations and self.trials[a]<4]
            if unknown:return super().answer(raw,min(unknown,key=lambda a:(self.trials[a],a)),{},'reference_orientation_inquiry',extra)
            if len(self.orientations)>=2:return dict(done=True,action=None,data={})
        return super().answer(raw,action,data,tag,extra)
    def issue(self,raw,action,data,phase,route=None,extra=None):
        if phase=='goal_route' and self.reference_targets(raw) and len(self.orientations)>=2:return dict(done=True,action=None,data={})
        return super().issue(raw,action,data,phase,route,extra)
