"""Finish an available one-step goal before pursuing an indirect reference hypothesis."""
from matrix_reference_intermediate_v4 import Agent as Base
from matrix_intermediate_learner_v4 import Agent as MemoryBase
from matrix_intermediate_learner_v3 import inside
class Agent(Base):
    def answer(self,raw,action,data,tag,extra=None):
        if tag=='move_toward_visual_goal' and self.moving and action in self.motions:
            m=self.motions[action]['delta'];y,x=self.moving['box'][:2];q=y+m[0],x+m[1]
            if any(inside(q[0],q[1],g['box']) for g in self.goals):return MemoryBase.answer(self,raw,action,data,tag,extra)
        return super().answer(raw,action,data,tag,extra)
