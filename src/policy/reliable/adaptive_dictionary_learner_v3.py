"""Allow the remembered-query expert to seek evidence when no dictionary plan exists."""
from adaptive_dictionary_learner_v2 import Learner as Base
from program_probe_learner import Learner as Program

class Learner(Base):
    def __init__(self):
        super().__init__();self.program=Program()

    def choose(self,obs):
        if obs['state']=='NOT_FINISHED' and not self.program.active and self.program.query_memory and super().propose(obs) is None:
            return self.program.choose(obs)
        return super().choose(obs)
