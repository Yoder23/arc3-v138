"""Re-observe after reset while retaining verified skills and attempted hypotheses."""
from collections import Counter
import copy
from matrix_intermediate_learner_v3 import Agent as Base

class Agent(Base):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.failure_memory=[];self.reset_memory=[];self.episode_attempts=set();self.resets_by_level=Counter()
    def answer(self,raw,action,data,tag,extra=None):
        evidence=dict(failure_memory=copy.deepcopy(self.failure_memory),reset_memory=copy.deepcopy(self.reset_memory))
        evidence.update(extra or {})
        return super().answer(raw,action,data,tag,evidence)
    def respond(self,raw):
        if self.level is not None and raw['levels_completed']!=self.level:self.episode_attempts=set()
        if raw['state']=='GAME_OVER':
            old=self.previous
            if old and old['action']!=0:
                self.episode_attempts.update(self.attempted)
                self.failure_memory.append(dict(source=old['source'],level=self.level,action=old['action'],data=copy.deepcopy(old['data']),attempted=sorted(self.episode_attempts),outcome='observed_game_over',causality='preceding_action_only_not_a_causal_claim'))
                self.resets_by_level[self.level]+=1
            if self.resets_by_level[self.level]>2:return dict(done=True,action=None,data={})
        if self.previous and self.previous['action']==0 and raw['state']=='NOT_FINISHED':
            source=self.previous['source']
            self.episode_bank.append(dict(level=self.level,motions=copy.deepcopy(self.motions),experiences=copy.deepcopy(self.experiences),program=self.program_index,ended_at_reset=source))
            self.reset_memory.append(dict(source=source,level=self.level,retained_skills=copy.deepcopy(self.input_motion_memory),attempted=sorted(self.episode_attempts)))
            self.previous=None;self.grid=None;self.edit=None;self.motions={};self.moving=None;self.goals=[];self.trials=Counter();self.blocked=set();self.passable=set();self.program_index=0;self.contact=None
            self.exploring=False;self.experiment=None;self.selection_record=None;self.extra_actions=0;self.context_revisions=[];self.attempted=set(self.episode_attempts)
        return super().respond(raw)
