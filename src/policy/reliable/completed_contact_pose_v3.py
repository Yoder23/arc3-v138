"""Give discrete controls four paired passes before trying a contact experiment."""
from completed_contact_pose_v2 import Learner as Original
from visual_transform_learner import public

class Learner(Original):
    def propose(self,raw):
        c=super().propose(raw)
        if c and c['kind']=='pose_contact_experiment':
            n=len(set(public(raw)['available_actions'])&{1,2,3,4,5,7})
            if self.keyboard_steps<max(24,8*n):return None
        return c
