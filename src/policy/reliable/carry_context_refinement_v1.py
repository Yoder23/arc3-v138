"""Refine a motion model's context after its own observed prediction fails."""
from collections import Counter
import copy
from carry_interaction_learner_v13 import Controller as Base
from observed_joint_routes_v1 import Memory

def mode(v):
    b=v['body'];y,x,_,_=b['box'];a,c,h,w=b['fill_box']
    counts=Counter((z['frame_ink'],z['inner_ink']) for z in v['cargo'])
    return (a-y,c-x,h,w,tuple(sorted(counts.items())))

class Controller(Base):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.context_models={};self.refutation_evidence=[];self.expected_joint=None
    def record(self,raw,v):
        old=self.previous;offset=self.held;expected=self.expected_joint
        self.expected_joint=None
        super().record(raw,v)
        if (old and old['view'] and v and old['raw']['state']==raw['state']=='NOT_FINISHED'
            and old['raw']['levels_completed']==raw['levels_completed']):
            actual=self.geometric_state(v)
            if expected and expected['source']==old['t'] and actual!=expected['next_state']:
                if old['t'] not in self.refutation_evidence:self.refutation_evidence.append(old['t'])
            if self.held==offset and old['action'] in self.motions:
                key=(self.level,offset,mode(old['view']))
                model=self.context_models.setdefault(key,Memory())
                model.observe(self.geometric_state(old['view']),old['action'],actual,old['t'],offset)
        if raw['state']=='GAME_OVER' and not self.retain:
            self.context_models.clear();self.refutation_evidence.clear()
    def conditional_models(self,v):
        signature=mode(v)
        return {(level,offset):model for (level,offset,observed),model in self.context_models.items()
                if level==self.level and observed==signature}
    def route(self,v,target,offset=None):
        if not self.refutation_evidence:return super().route(v,target,offset)
        original=self.joint_memory;self.joint_memory=self.conditional_models(v)
        try:return super().route(v,target,offset)
        finally:self.joint_memory=original
    def answer(self,raw,v,action,tag):
        original=self.joint_memory
        if self.refutation_evidence and v:self.joint_memory=self.conditional_models(v)
        try:response=super().answer(raw,v,action,tag)
        finally:self.joint_memory=original
        c=response['certificate']
        if self.refutation_evidence and v:
            c['context_refinement']=dict(hypothesis='separate_visible_modes_after_prediction_error',
                refutations=list(self.refutation_evidence),mode=copy.deepcopy(mode(v)))
        known=c.get('joint_memory',{}).get('known_first_step')
        if known:self.expected_joint=dict(source=self.t-1,next_state=known['next_state'])
        return response
