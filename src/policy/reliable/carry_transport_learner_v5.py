"""Retain verified regrasp skills without banning their reuse on another object."""
import copy
from carry_transport_learner_v4 import Controller as Base

class Controller(Base):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.regrasp_skill_archive={}
    def record(self,raw,v):
        old=self.previous
        super().record(raw,v)
        if raw['state']=='GAME_OVER' and not self.retain:self.regrasp_skill_archive={}
        if self.transport_active() and old and v and self.held is not None and self.attachment:
            for r in self.regrasp_skill_archive.values():
                if (r['level']==self.level and 'pick_source' in r and r['pick_source']<old['t']
                    and 'verification_source' not in r and tuple(r['new_offset'])==tuple(self.held)
                    and self.attachment['support']==old['t'] and sum(abs(x) for x in self.held)==v['n']):
                    r['verification_source']=old['t']
            verified={i for i,r in self.regrasp_skill_archive.items() if 'verification_source' in r}
            # The three-unresolved-trial bound remains. A measured successful
            # skill is retained and may be tried with a new physical object.
            self.regrasp_trials=[r for r in self.regrasp_trials if r['source'] not in verified]
    def answer(self,raw,v,action,tag):
        response=super().answer(raw,v,action,tag)
        if self.transport_active():
            pending=response['certificate'].get('regrasp_experiment')
            if pending:
                r=self.regrasp_skill_archive.setdefault(pending['source'],dict(level=pending['level'],source=pending['source'],new_offset=tuple(pending['new_offset'])))
                if pending['phase']=='picked':r['pick_source']=self.t-1
            skills=[copy.deepcopy(r) for r in self.regrasp_skill_archive.values() if r['level']==self.level and 'verification_source' in r]
            if skills:response['certificate']['retained_regrasp_skills']=skills
        return response
