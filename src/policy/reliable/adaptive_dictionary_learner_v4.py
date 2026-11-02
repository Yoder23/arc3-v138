"""Retained experts with deliberate interventions after observed exploration stagnation."""
from adaptive_dictionary_learner_v3 import Learner as Base
from program_stagnation_learner import Learner as Program

class Learner(Base):
    def __init__(self):
        super().__init__();self.program=Program()
