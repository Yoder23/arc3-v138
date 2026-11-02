"""Preserve established plans; use supported tentative programs to guide inquiry."""
from parallel_optimistic_model_v3 import Learner as Structured
from context_inquiry_learner_v1 import Learner as Prior,Controller as BaseController
class Learner(Prior):
    def __init__(self,retain=True):
        super().__init__(retain);self.structured=Structured(retain)
    def observe(self,raw,action=None,data=None):
        self.structured.observe(raw,action,data);super().observe(raw,action,data)
    def propose(self,raw):
        prior=super().propose(raw)
        if prior and prior['kind']=='track_conjunction_plan':return prior
        return self.structured.propose(raw) or prior
class Controller(BaseController):
    def __init__(self,prior=None,retain=True):
        super().__init__(prior,retain);self.learner=Learner(retain)
