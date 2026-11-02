"""Preserve distinct simultaneous deliveries as well as repeat deliveries."""
from carry_transport_learner_v8 import Controller as Base
from observed_transport_memory_v4 import Memory

class Controller(Base):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.transport=Memory()
