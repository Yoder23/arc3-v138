"""Retain direct, fixed-dictionary and composed-menu experts across selection."""
from adaptive_dictionary_learner_v9 import Learner as Base
from composed_menu_learner_v2 import Learner as Composed

class Learner(Base):
    def __init__(self):
        super().__init__();self.composed=Composed()

    def observe(self,obs,action=None):
        self.composed.observe(obs,action)
        super().observe(obs,action)

    def propose(self,obs):
        prior=super().propose(obs)
        if self.composed.active or prior is None:
            cert=self.composed.propose(obs)
            if cert:return dict(cert,dictionary_expert='composed')
        return prior

    def commit(self,cert):
        if cert.get('dictionary_expert')=='composed':self.composed.commit(cert)
        else:super().commit(cert)

    def choose(self,obs):
        cert=self.propose(obs)
        if cert:self.commit(cert);return cert['action']
        return super().choose(obs)
