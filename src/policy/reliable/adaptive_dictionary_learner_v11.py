"""Preserve an existing dictionary interpretation when its next step is uncertain."""
from adaptive_dictionary_learner_v10 import Learner as Base
from adaptive_dictionary_learner_v9 import Learner as Prior

class Learner(Base):
    def propose(self,obs):
        prior=Prior.propose(self,obs)
        unclaimed=prior is None and not self.hypotheses and not self.program.query_memory
        if self.composed.active or unclaimed:
            cert=self.composed.propose(obs)
            if cert:return dict(cert,dictionary_expert='composed')
        return prior
