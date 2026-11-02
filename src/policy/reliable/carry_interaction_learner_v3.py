"""Archive learned episode facts and re-ground goals at observed level boundaries."""
import copy
from carry_interaction_learner_v2 import Controller as Base

class Controller(Base):
    def __init__(self,prior=None,retain=True):
        super().__init__(prior,retain);self.level=None;self.episode_bank=[]
    def respond(self,raw):
        level=raw['levels_completed']
        if self.level is not None and level!=self.level:
            self.episode_bank.append(dict(level=self.level,goal=copy.deepcopy(self.goal),motions=copy.deepcopy(self.motions),
                signature=self.signature,attachment=copy.deepcopy(self.attachment),boundary_observed_at=self.t))
            self.previous=None;self.signature=None;self.phase=None;self.goal=None;self.motions={};self.blocked=set()
            self.held=None;self.attachment=None;self.mode=None;self.target=None;self.trials.clear();self.no_goal_steps=0
        self.level=level
        return super().respond(raw)
