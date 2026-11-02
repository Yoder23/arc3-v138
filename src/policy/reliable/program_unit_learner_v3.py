"""Revise intervention units after a real plan or exploration refutes a known glyph selection."""
import copy
from program_unit_interface import Learner as Base
from editable_program_learner import values as glyph_values
from atomic_word_programs import values as word_values,signature
from panel_hypotheses_v2 import digest

class Learner(Base):
    def __init__(self):
        super().__init__();self.unit_refutation_support=[]
    def observe(self,obs,action=None):
        old=self.glyph.previous;prior=self.glyph.prior_layouts
        planned=copy.deepcopy(self.glyph.pending);word_index=self.word.current
        progress=old is not None and (old['levels_completed']!=obs['levels_completed'] or obs['state']=='WIN')
        super().observe(obs,action)
        if progress:self.unit_refutation_support=[]
        if self.word_mode or old is None or progress or action in (None,0) or old['state']!=obs['state'] or obs['state']!='NOT_FINISHED':return
        if not planned or planned['action']!=action or planned['kind'] not in ('edit_plan','discover_edit_cycle') or planned.get('selected_index') is None or word_index is None:return
        for a in prior:
            for b in self.glyph.prior_layouts:
                if signature(a)!=signature(b) or [p['box'] for p in a['panels']]!=[p['box'] for p in b['panels']]:continue
                ga,gb=glyph_values(a),glyph_values(b);wa,wb=word_values(a),word_values(b)
                changed=[i for i,(x,y) in enumerate(zip(ga,gb)) if x!=y]
                words=[i for i,(x,y) in enumerate(zip(wa,wb)) if x!=y]
                if len(changed)!=1 or changed[0]==planned['selected_index'] or words!=[word_index]:continue
                proof=dict(event=digest(dict(before=old,after=obs,action=action)),
                    glyph_selected_index=planned['selected_index'],word_selected_index=word_index,
                    actual_glyph_index=changed[0],selected_certificate=digest(planned))
                self.unit_refutation_support.append(proof);self.word_mode=True

    def propose(self,obs):
        c=super().propose(obs)
        if c and c.get('control_unit')=='panel_word' and self.unit_refutation_support:
            return dict(c,unit_refutation_support=copy.deepcopy(self.unit_refutation_support))
        return c
