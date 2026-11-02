"""Escalate exploration only after two complete control passes reveal no editor."""
from atomic_program_frontier_learner import Learner as Base

class Learner(Base):
    def choose(self,obs):
        if obs['state']=='NOT_FINISHED' and self.query_memory and not self.active:
            legal=sorted(set(obs['available_actions'])&{1,2,3,4,5,7})
            n=sum(self.counts[a] for a in legal)
            if legal and n>=2*len(legal):
                return legal[((n-2*len(legal))//2)%len(legal)]
        return super().choose(obs)
