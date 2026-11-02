"""Test an observed relocation program after local targets open an unreachable goal."""
import copy
from matrix_remaining_interactions_v1 import Agent as Base
from matrix_intermediate_learner_v3 import reachable,path,inside
from observed_program_completion_v1 import ProgramEditLoop
class Agent(Base):
 def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.relocation_attempts=set();self.relocation_active=False
 def respond(self,raw):
  if self.relocation_active and self.edit and self.level==raw['levels_completed'] and raw['state']=='NOT_FINISHED':
   self.observe(raw);proposal=self.edit.propose(raw)
   if proposal:return self.answer(raw,proposal['action'],proposal['data'],'verify_input_edit',dict(edit=proposal['certificate'],edit_start=self.edit_started_at))
   if self.edit.completed(raw):self.edit=None;self.relocation_active=False;self.exploring=False;self.experiment=None;self.contact=None
  return super().respond(raw)
 def finish(self,raw,outcome):
  if outcome=='input_completed' and self.moving and self.effect_seen_level==raw['levels_completed'] and not self.reference_targets(raw):
   parents,_=reachable(self,raw)
   reachable_goals=[q for q in parents for g in self.goals if inside(q[0],q[1],g['box'])]
   if self.goals and not reachable_goals:
    candidates=[(m,b)for m in self.body_program_memory for b in self.program_bindings if m['effect']=='observed_body_relocation' and m['indices']==b['reference']['indices'] and m['before']['ink']==self.moving['ink']]
    for m,b in reversed(candidates):
     key=(self.level,tuple(self.moving['box'][2:]),tuple(m['indices']),tuple(tuple(g['box'])for g in self.goals))
     if key in self.relocation_attempts:continue
     self.relocation_attempts.add(key);e=self.ranged;self.ranged_memory.append(dict(start=e['start'],end=self.t,landmark=e['landmark'],pose=e['pose'],direction=e['direction'],outcome=outcome,world_effect_unconfirmed=True));self.ranged=None;self.experiment=None;self.contact=None;self.exploring=False;self.composition_queue=None
     chosen=b['points'];self.programs=[chosen]+[p for p in self.programs if p!=chosen];self.program_index=0;self.edit=ProgramEditLoop(chosen,self.grid,self.t);self.program_editors.append(self.edit);self.edit_started_at=self.t;self.relocation_active=True
     proposal=self.edit.propose(raw)
     if proposal:return self.answer(raw,proposal['action'],proposal['data'],'verify_input_edit',dict(edit=proposal['certificate'],edit_start=self.t,relocation_goal_hypothesis=dict(effect_source=m['source'],binding=copy.deepcopy(b),goal_boxes=[g['box']for g in self.goals],size_transfer=m['before']['box'][2:]!=self.moving['box'][2:],goal_unreachable_by_observed_motion=True)))
  return super().finish(raw,outcome)
