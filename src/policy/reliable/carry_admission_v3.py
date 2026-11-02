"""Conservative integration of the carry skill with measured public gains."""
from carry_interaction_learner_v7 import Controller as Base
from carry_admission_v2 import admissible
from visual_transform_learner import public

class Controller(Base):
    def __init__(self,prior=None,retain=True):
        super().__init__(prior,retain);self.admission_checked=False;self.admitted=False
    def respond(self,raw):
        obs=public(raw)
        if not self.admission_checked and obs['state']=='NOT_FINISHED':
            self.admitted=admissible(obs);self.admission_checked=True
        if not self.admitted and self.prior is not None:return self.prior.respond(obs)
        return super().respond(obs)
