"""Retain repeated delivery episodes so timing can transfer between objects."""
from carry_transport_learner_v7 import Controller as Base
from observed_transport_memory_v3 import Memory

class Controller(Base):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.transport=Memory()
    def record(self,raw,v):
        if raw['state']=='GAME_OVER' and not self.retain:self.delivery_releases={}
        return super().record(raw,v)
