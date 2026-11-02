"""Keep supported geometric plans; use local correspondence when they cannot plan."""
from global_correspondence_base_v1 import Learner as Local,Controller as BaseController
from segmented_correspondence_learner_v1 import Learner as Geometric

class Learner(Local):
    def __init__(self,retain=True):
        super().__init__(retain);self.established=Geometric(retain)
    def observe(self,raw,action=None,data=None):
        self.established.observe(raw,action,data)
        super().observe(raw,action,data)
    def propose(self,raw):
        earlier=self.established.propose(raw)
        if earlier and earlier['kind']=='track_conjunction_plan':return earlier
        broader=super().propose(raw)
        if broader and broader['kind']=='track_conjunction_plan':return broader
        return earlier or broader

class Controller(BaseController):
    def __init__(self,prior=None,retain=True):
        super().__init__(prior,retain);self.learner=Learner(retain)
