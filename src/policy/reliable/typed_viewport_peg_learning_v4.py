"""Acquire a permanent stepping-token rule through an actual highlighted jump."""
import copy
from typed_peg_inquiry_v2 import Agent as Inquiry
from viewport_peg_learning_v8 import Agent as Core
from peg_world_memory_v9 import Memory
class Agent:
    def __init__(self,prior=None):self.prior=prior;self.active=True;self.inquiry=Inquiry();self.learner=None;self.attempted=False
    def respond(self,raw):
        if self.learner:return self.learner.respond(raw)
        r=self.inquiry.respond(raw)
        if not r['done']or self.attempted:return r
        self.attempted=True;p=self.inquiry.inquiry;outcome=self.inquiry.outcome
        if not p or not outcome or not outcome.get('selection_activated')or raw['state']!='NOT_FINISHED'or raw['levels_completed']!=p['level']:return r
        before=self.inquiry.selected['frame'];after=raw['frame'];a,b,z=p['local_jump'];k=(p['size']-1)//2;size=p['size']
        if not(before[a[0]+k][a[1]+k]==p['mark']and after[a[0]+k][a[1]+k]==p['field']and after[z[0]+k][z[1]+k]==p['mark']):return r
        patch=lambda f:tuple(tuple(f[y][x]for x in range(b[1]-1,b[1]+size+1))for y in range(b[0]-1,b[0]+size+1))
        if patch(before)!=patch(after):return r
        rule=dict(source=outcome['landing_source'],selection_source=p['source'],level=p['level'],local_jump=p['local_jump'],field=p['field'],mark=p['mark'],center_ink=p['intermediate_ink'],size=size,pitch=p['pitch'],patch=patch(before),hypothesis='observed_jump_preserves_distinct_intermediate_token')
        self.learner=Core();self.learner.__dict__.update(copy.deepcopy(self.inquiry.prefix.__dict__));self.learner.t=self.inquiry.t;self.learner.previous=None;self.learner.retained_plan=None;self.learner.memory=Memory.transfer(self.inquiry.prefix.memory,rule)
        return self.learner.respond(raw)
