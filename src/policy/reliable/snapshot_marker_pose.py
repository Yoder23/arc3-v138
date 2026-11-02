"""Use a remembered exact shape as a tentative goal when stronger skills offer none."""
from completed_marker_pose import Learner as Base
from snapshot_pose_hypotheses import propose

class Learner(Base):
    def propose(self,raw):
        existing=super().propose(raw)
        return existing if existing else propose(self,raw)
