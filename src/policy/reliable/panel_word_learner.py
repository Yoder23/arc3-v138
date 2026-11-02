"""Remember demonstrated words; revise goals only after actual completed trials."""
import copy
from collections import Counter
from panel_control_learner_v2 import Learner as Base
from panel_control_learner import identity
from panel_word_hypotheses import candidates
from panel_hypotheses_v2 import digest


class Learner(Base):
    def __init__(self):
        super().__init__()
        self.dictionaries=[]
        self.failed_goals=Counter()
        self.goal_trials=[]
        self.last_completed=None

    def scene(self,obs):
        parsed=candidates(obs,self.dictionaries)
        if parsed['maps']:
            self.dictionaries=copy.deepcopy(parsed['maps'])
        self.hypotheses=copy.deepcopy(parsed['proposals'])
        return [dict(box=p['target_box'],source_box=p['source_box'],
                     classes=tuple(identity(g) for g in p['actual']),
                     expected=tuple(identity(g) for g in p['expected']),proposal=p)
                for p in parsed['proposals']]

    @staticmethod
    def key(s):
        return (s['source_box'],s['box'],s['expected'])

    def observe(self,obs,action=None):
        old=self.previous
        progress=old is not None and (obs['levels_completed']!=old['levels_completed'] or obs['state']=='WIN')
        if progress:
            self.dictionaries=[];self.failed_goals.clear();self.last_completed=None
        super().observe(obs,action)
        # A completed visible output after an actual action without progress is a
        # failed goal trial, not evidence that an unobserved/partial goal failed.
        if old is not None and action is not None and not progress and action!=0 and obs['state']=='NOT_FINISHED':
            complete=[s for s in self.scenes if s['classes']==s['expected']]
            for s in complete:
                key=self.key(s)
                marker=(key,tuple(tuple(row) for row in obs['frame']))
                if marker!=self.last_completed:
                    self.failed_goals[key]+=1
                    self.goal_trials.append(dict(goal=key,before=digest(old),after=digest(obs),action=action))
                    self.last_completed=marker
        if self.scenes:
            self.snapshot=min(self.scenes,key=lambda s:(
                -sum(r['box']==s['box'] for r in self.edit_rows),
                self.failed_goals[self.key(s)],s['box'],s['source_box'],
                len(s['proposal']['derivation']),s['expected']))
        if action==0:
            self.last_completed=None
