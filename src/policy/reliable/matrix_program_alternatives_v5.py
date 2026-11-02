"""Retain failed approaches, then rebuild an alternative observed program after reset."""
import copy
from collections import Counter
from matrix_ranged_terminal_v3 import Agent as Base
from observed_program_completion_v1 import ProgramEditLoop
class Agent(Base):
 def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.program_alternatives=[];self.alternative_levels=set();self.desired_program=None;self.extended_resets=Counter()
 def respond(self,raw):
  if self.level is not None and raw['levels_completed']!=self.level:self.desired_program=None
  r=super().respond(raw)
  if not r['done']:return r
  if raw['state'] in ('GAME_OVER','NOT_FINISHED') and self.level not in self.alternative_levels and len(self.program_bindings)>1:
   self.alternative_levels.add(self.level);chosen=self.program_bindings[1];self.desired_program=chosen['reference']['ink'];self.program_alternatives.append(dict(source=self.t,level=self.level,prior_program=copy.deepcopy(self.program_bindings[0]['points']),chosen_program=copy.deepcopy(chosen['points']),prior_attempts=copy.deepcopy(sorted(self.ranged_attempts)),reason='prior_program_did_not_finish_observed_goal',goal_unconfirmed=True));self.ranged_steps=0;self.ranged_attempts=set()
  if raw['state']=='GAME_OVER' and self.desired_program is not None and self.extended_resets[self.level]<2:
   self.extended_resets[self.level]+=1;return self.answer(raw,0,{},'reset_after_failure')
  return r
 def answer(self,raw,action,data,tag,extra=None):
  r=super().answer(raw,action,data,tag,extra)
  if r['done']:return r
  if tag=='verify_input_edit' and self.program_bank_bound_at==self.t-1 and self.desired_program is not None:
   binding=next((b for b in self.program_bindings if b['reference']['ink']==self.desired_program),None)
   if binding:
    chosen=binding['points'];self.programs=[chosen]+[p for p in self.programs if p!=chosen];self.program_index=0;self.edit=ProgramEditLoop(chosen,self.grid,self.t-1);self.program_editors.append(self.edit);self.edit_started_at=self.t-1;proposal=self.edit.propose(raw);r['action']=proposal['action'];r['data']=proposal['data'];r['certificate'].update(edit=proposal['certificate'],edit_start=self.t-1,program_index=0);self.previous.update(action=r['action'],data=copy.deepcopy(r['data']),certificate=copy.deepcopy(r['certificate']))
  if self.program_alternatives:r['certificate']['program_alternatives']=copy.deepcopy(self.program_alternatives);self.previous['certificate']=copy.deepcopy(r['certificate'])
  return r
