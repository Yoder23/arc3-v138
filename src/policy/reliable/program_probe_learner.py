"""Try short repeated interventions when a remembered query has no known editor."""
from program_retained_frontier_learner import Learner as Base

class Learner(Base):
    def choose(self,obs):
        if obs['state']=='NOT_FINISHED' and self.query_memory and not self.active:
            legal=sorted(set(obs['available_actions'])&{1,2,3,4,5,7})
            if legal:
                # Counts change only when observe receives an actual selected action.
                return legal[(sum(self.counts[a] for a in legal)//2)%len(legal)]
        return super().choose(obs)
