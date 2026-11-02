"""Retain both experts and use context-aware experiments for editable programs."""
from adaptive_dictionary_learner import Learner as Base
from program_retained_frontier_learner import Learner as Program

class Learner(Base):
    def __init__(self):
        super().__init__();self.program=Program()
