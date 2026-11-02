"""Retain intervention experts and prefer goals consistent with measured menus."""
from adaptive_dictionary_learner_v4 import Learner as Base
from cycle_feasible_program_learner import Learner as Program
class Learner(Base):
    def __init__(self):
        super().__init__()
        self.program=Program()
