"""Separate remote co-motion from a local grasp after transport is identified."""
from carry_transport_learner_v1 import Controller as Base
from observed_transport_memory_v2 import Memory

class Controller(Base):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.transport=Memory();self.remote_co_motion=[]
    def record(self,raw,v):
        super().record(raw,v)
        if self.transport_active() and v and self.held is not None and sum(abs(x) for x in self.held)!=v['n']:
            # An object far away can happen to move with the agent. This is
            # still actual co-motion, but it is not support for a local grasp.
            self.remote_co_motion.append(dict(level=self.level,support=self.attachment['support'],offset=self.held))
            self.held=None;self.attachment=None;self.mode=None
    def answer(self,raw,v,action,tag):
        response=super().answer(raw,v,action,tag)
        if self.transport_active() and self.remote_co_motion:
            response['certificate']['remote_co_motion_rejected_as_local_grasp']=[dict(r) for r in self.remote_co_motion if r['level']==self.level]
        return response
