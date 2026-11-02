"""Read-only compatibility for the dictionary router's remembered-query contract."""
from program_unit_learner import Learner as Base
class Learner(Base):
    @property
    def parsed(self):return self.glyph.parsed
    @property
    def query_memory(self):return (self.word if self.word_mode else self.glyph).query_memory
