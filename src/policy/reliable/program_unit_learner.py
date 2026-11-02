"""Retained glyph and word experts; coordinated interventions select the control unit."""
from program_stagnation_learner import Learner as Glyph
from atomic_program_stagnation_learner import Learner as Word
from atomic_word_programs import values,signature
from panel_hypotheses_v2 import digest

class Learner:
    def __init__(self):
        self.glyph=Glyph();self.word=Word();self.word_mode=False;self.unit_role_support=[]

    @property
    def active(self):return self.word.active if self.word_mode else self.glyph.active

    def observe(self,obs,action=None):
        old=self.word.previous;prior=self.word.prior_layouts
        progress=old is not None and (old['levels_completed']!=obs['levels_completed'] or obs['state']=='WIN')
        if progress:self.word_mode=False;self.unit_role_support=[]
        self.glyph.observe(obs,action);self.word.observe(obs,action)
        if old is None or progress or action in (None,0) or old['state']!=obs['state'] or obs['state']!='NOT_FINISHED':return
        for a in prior:
            for b in self.word.prior_layouts:
                if signature(a)!=signature(b) or [p['box'] for p in a['panels']]!=[p['box'] for p in b['panels']]:continue
                av,bv=values(a),values(b)
                if len(av)!=len(bv):continue
                changed=[i for i,(x,y) in enumerate(zip(av,bv)) if x!=y]
                if len(changed)!=1:continue
                i=changed[0];left,right=av[i][1],bv[i][1]
                if len(left)!=len(right) or sum(x!=y for x,y in zip(left,right))<2:continue
                self.word_mode=True;h=digest(dict(before=old,after=obs,action=action))
                if h not in self.unit_role_support:self.unit_role_support.append(h)

    def propose(self,obs):
        if not self.word_mode:return self.glyph.propose(obs)
        c=self.word.propose(obs)
        return dict(c,unit_role_support=list(self.unit_role_support)) if c else None

    def commit(self,cert):
        (self.word if cert.get('control_unit')=='panel_word' else self.glyph).commit(cert)

    def choose(self,obs):
        if obs['state'] in ('GAME_OVER','NOT_PLAYED'):return 0
        if obs['state']=='WIN':return None
        c=self.propose(obs)
        if c:self.commit(c);return c['action']
        return (self.word if self.word_mode else self.glyph).choose(obs)
