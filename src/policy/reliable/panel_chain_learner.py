"""Use retained alphabet chains within the existing learned-control/revision loop."""
import copy
from panel_word_learner import Learner as Base
from panel_word_hypotheses import identity
from panel_chain_hypotheses import candidates
class Learner(Base):
    def scene(self,obs):
        parsed=candidates(obs,self.dictionaries)
        if parsed['maps']:self.dictionaries=copy.deepcopy(parsed['maps'])
        self.hypotheses=copy.deepcopy(parsed['proposals'])
        return [dict(box=p['target_box'],source_box=p['source_box'],
                     classes=tuple(identity(g) for g in p['actual']),
                     expected=tuple(identity(g) for g in p['expected']),proposal=p)
                for p in parsed['proposals']]
