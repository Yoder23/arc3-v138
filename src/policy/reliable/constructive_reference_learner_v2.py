"""Preserve an existing composed-input interpretation before trying construction."""
from constructive_reference_learner_v1 import Learner as Construction
from centered_word_learner_v2 import Learner as Established

class Learner(Construction):
    def propose(self,raw):
        # A complete previously visible hierarchy with an actionable remembered
        # word must not be hidden by a speculative insertion with no goal. Once
        # a construction trial actually starts, preserve its own revision loop.
        if not any(t['operation']=='insert' for t in self.reference_trials):
            candidate=Established.propose(self,raw)
            if candidate and candidate.get('linked_input') and candidate.get('goal'):
                return candidate
        return super().propose(raw)
