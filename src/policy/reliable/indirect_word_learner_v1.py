"""Retain observed hierarchical input geometry alongside actual exchange learning."""
import copy
from observed_exchange_tool_learner import Learner as Base
from indirect_word_geometry_v1 import parse
from literal_word_rows import values
from visual_transform_learner import public

class Learner(Base):
    def __init__(self,*,retain=True):
        super().__init__(retain=retain);self.linked_rows={}

    def observe(self,raw,action=None,data=None):
        obs=public(raw);super().observe(obs,action,data)
        if obs['state']!='NOT_FINISHED':return
        for structure in parse(obs['frame']):
            row=structure['leaves']
            if len(self.rows)<64 and values(obs['frame'],row) is not None:
                self.rows.setdefault(row,len(self.history))
                self.linked_rows.setdefault(row,dict(observed_at=len(self.history),structure=copy.deepcopy(structure)))

    def propose(self,raw):
        c=super().propose(raw)
        if c:
            row=c['goal']['target'] if c.get('goal') else c.get('target')
            if row in self.linked_rows:c['linked_input']=copy.deepcopy(self.linked_rows[row])
        return c
