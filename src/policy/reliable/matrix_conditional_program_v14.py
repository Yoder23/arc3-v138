"""Terminal reset decisions cannot assert a body in the current frame."""
from matrix_conditional_program_v13 import Agent as Base
class Agent(Base):
    def answer(self,raw,action,data,tag,extra=None):
        extra=dict(extra or {})
        if raw['state']!='NOT_FINISHED':extra['moving']=None
        return super().answer(raw,action,data,tag,extra)
