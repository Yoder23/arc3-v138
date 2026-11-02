"""Return to cheaper goal routes when a control inquiry resolves missing knowledge."""
from selectable_multi_object_learner_v13 import Agent as Base
class Agent(Base):
    def joint_response(self,raw):
        old=self.previous
        if old and old['source'] in self.conditional_inquiries.values() and any(m['source']==old['source'] for m in self.motions.values()):
            # This observation was already processed. Keep its learned effects and
            # avoid ingesting the same transition twice while switching planners.
            self.joint_mode=False;self.previous=None
            return super().respond(raw)
        return super().joint_response(raw)
