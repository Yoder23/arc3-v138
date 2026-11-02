"""Acquire mixed-size and hollow symbols without assigning their meaning."""
import copy
from indirect_word_learner_v1 import Learner as Prior
from centered_word_geometry_v2 import parse
from centered_symbol_rows_v1 import layouts,mixed_groups
from literal_word_rows import values
from literal_word_goals import channels
from visual_transform_learner import public

class Learner(Prior):
    def observe(self,raw,action=None,data=None):
        obs=public(raw);super().observe(obs,action,data)
        if obs['state']!='NOT_FINISHED':return
        groups=mixed_groups(obs['frame'])
        if groups:
            for row in layouts(obs['frame']):
                if len(self.rows)<64:self.rows.setdefault(row,len(self.history))
                if row in self.rows:
                    for channel,word in channels(obs['frame'],row).items():
                        if len(set(word))>=2 and len(self.sources)<192:
                            self.sources.setdefault((row,channel,word),len(self.history))
        for structure in parse(obs['frame']):
            row=structure['leaves']
            if row not in self.linked_rows and len(self.rows)<64 and values(obs['frame'],row) is not None:
                self.rows.setdefault(row,len(self.history))
                self.linked_rows[row]=dict(observed_at=len(self.history),structure=copy.deepcopy(structure),centered_core_representation=True)
