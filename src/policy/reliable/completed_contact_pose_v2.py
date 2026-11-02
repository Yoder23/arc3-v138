"""Retain ordinary retry knowledge; explore contact only after useful plans stall."""
from completed_contact_pose import Learner as Original
from completed_pose_learner_v2 import Learner as Pose
from visual_transform_learner import public,unique

class Learner(Original):
    def observe(self,raw,action=None,data=None):
        obs=public(raw);pending=self.pending
        # Before any contact intervention, retain the established pose learner's
        # retry semantics. Contact-conditioned evidence still needs revalidation.
        if action==0 and self.boundary is None:
            Pose.observe(self,obs,action);self.keyboard_steps=0
        else:super().observe(obs,action,data)
        if pending and action==pending['action']:
            expected=pending['path'][0]['after']
            if any(p==expected for p in self.perceive(obs['frame']).values()):
                self.keyboard_steps=0
