"""Retained dictionary experts; actual rule edits activate program synthesis."""
from panel_chain_learner import Learner as Chain
from editable_program_learner import Learner as Program

class Learner(Chain):
    def __init__(self):
        super().__init__();self.program=Program()

    def observe(self,obs,action=None):
        # Both experts receive the selected action, including external interventions.
        # Neither discarded proposal nor expert selection is a learning event.
        self.program.observe(obs,action)
        super().observe(obs,action)

    def propose(self,obs):
        return self.program.propose(obs) if self.program.active else super().propose(obs)

    def commit(self,cert):
        if cert.get('program_mode'):self.program.commit(cert)
        else:super().commit(cert)

    def choose(self,obs):
        return self.program.choose(obs) if self.program.active else super().choose(obs)
