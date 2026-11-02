"""Keep dual intervention experts while revising tentative goals using actual cycles."""
from program_unit_learner_v3 import Learner as Base
from cycle_feasible_word_learner import Learner as Word
class Learner(Base):
    def __init__(self):
        super().__init__()
        self.word=Word()
