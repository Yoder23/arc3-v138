"""Remember observed body transformations and test them as prerequisites in later scenes."""
import copy
from matrix_effect_goal_transfer_v3 import Agent as Base
from matrix_motion_learner_v6 import objects
from observed_program_completion_v1 import ProgramEditLoop
class Agent(Base):
 def __init__(self,*args,**kwargs):
  super().__init__(*args,**kwargs);self.body_program_memory=[];self.effect_sources=set();self.prerequisite_use=None;self.composition_queue=None
 def respond(self,raw):
  old=self.previous
  if old and old['action']==6 and old['raw']['levels_completed']==raw['levels_completed'] and raw['state']=='NOT_FINISHED' and old['source'] not in self.effect_sources:
   c=old['certificate'];edit=c.get('edit');grid=c.get('grid')
   if edit and grid:
    selected=[q['point'] for q in edit.get('previous_evidence',[]) if q.get('changed')]+[edit['point']]
    binding=next((b for b in c.get('program_bindings',[]) if set(map(tuple,b['points']))==set(map(tuple,selected))),None)
    if binding:
     before=[o for o in objects(old['raw']['frame'],[grid['box']]) if o.get('parts')];after=[o for o in objects(raw['frame'],[grid['box']]) if o.get('parts')]
     pairs=[(a,b) for a in before for b in after if a['ink']==b['ink'] and a['box']!=b['box']]
     if len(pairs)==1:
      a,b=pairs[0];self.effect_sources.add(old['source']);self.body_program_memory.append(dict(level=raw['levels_completed'],source=old['source'],binding=copy.deepcopy(binding),before=a,after=b,indices=binding['reference']['indices'],effect='observed_body_size_change' if a['box'][2:]!=b['box'][2:] else 'observed_body_relocation',causality='single_program_intervention_hypothesis'))
  if self.composition_queue and self.edit and self.previous and self.previous['certificate']['tag']=='verify_input_edit':
   proposal=self.edit.propose(raw)
   if proposal:return self.answer(raw,proposal['action'],proposal['data'],'verify_input_edit',dict(edit=proposal['certificate'],edit_start=self.edit_started_at))
   if proposal is None and self.edit.completed(raw):
    chosen=self.composition_queue;self.composition_queue=None;self.programs=[chosen]+[p for p in self.programs if p!=chosen];self.program_index=0;self.edit=ProgramEditLoop(chosen,self.grid,self.t);self.program_editors.append(self.edit);self.edit_started_at=self.t;proposal=self.edit.propose(raw)
    if proposal:return self.answer(raw,proposal['action'],proposal['data'],'verify_input_edit',dict(edit=proposal['certificate'],edit_start=self.t,composition_hypothesis='test_other_observed_program_after_learned_size_change'))
  return super().respond(raw)
 def answer(self,raw,action,data,tag,extra=None):
  fresh=tag=='verify_input_edit' and self.grid and self.program_bank_bound_at!=self.grid['observed_at']
  r=super().answer(raw,action,data,tag,extra)
  if r['done']:return r
  if fresh and self.body_program_memory:
   bodies=[o for o in objects(raw['frame'],[self.grid['box']]) if o.get('parts')]
   candidates=[(m,b) for m in self.body_program_memory for b in self.program_bindings if b['reference']['indices']==m['indices'] and m['after']['box'][2]<m['before']['box'][2] and any(o['ink']==m['before']['ink'] and o['box'][2:]==m['before']['box'][2:] for o in bodies)]
   if candidates:
    m,b=candidates[-1];chosen=b['points'];self.composition_queue=copy.deepcopy(self.program_bindings[0]['points']) if self.program_bindings[0]['points']!=chosen and m['level']<raw['levels_completed'] else None;self.programs=[chosen]+[p for p in self.programs if p!=chosen];self.program_index=0;self.edit=ProgramEditLoop(chosen,self.grid,self.t-1);self.program_editors.append(self.edit);self.edit_started_at=self.t-1;proposal=self.edit.propose(raw);r['action']=proposal['action'];r['data']=proposal['data'];r['certificate'].update(edit=proposal['certificate'],edit_start=self.t-1,program_index=0);self.prerequisite_use=dict(source=m['source'],binding=copy.deepcopy(b),hypothesis='test_retained_size_change_before_navigation')
  r['certificate']['body_program_memory']=copy.deepcopy(self.body_program_memory)
  if self.prerequisite_use:r['certificate']['prerequisite_use']=copy.deepcopy(self.prerequisite_use)
  self.previous.update(action=r['action'],data=copy.deepcopy(r['data']),certificate=copy.deepcopy(r['certificate']))
  return r

 def finish(self,raw,outcome):
  if not self.motions:
   e=self.ranged;self.ranged_memory.append(dict(start=e['start'],end=self.t,landmark=e['landmark'],pose=e['pose'],direction=e['direction'],outcome=outcome,world_effect_unconfirmed=True));self.ranged=None;self.heading_witness=None;self.orientations={}
   return self.answer(raw,min(a for a in raw['available_actions'] if a not in (0,6,7)),{},'motion_inquiry')
  return super().finish(raw,outcome)
