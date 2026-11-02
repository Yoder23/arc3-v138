"""Test retained body-size skills when exact aiming requires another geometry."""
import copy
from types import SimpleNamespace
from matrix_program_effect_memory_v6 import Agent as Base
from matrix_motion_learner_v6 import objects
from matrix_intermediate_learner_v3 import reachable,path
from matrix_reference_programs_v1 import programs
from observed_program_completion_v1 import ProgramEditLoop
class Agent(Base):
 def __init__(self,*args,**kwargs):
  super().__init__(*args,**kwargs);self.control_skill_bank=[];self.control_sources=set();self.observed_source=None;self.size_plan=None;self.size_plan_attempts=set();self.retrieved_controls=[];self.live_alternative_attempts=set()
 def observe(self,raw):
  key=self.previous['source'] if self.previous else None
  if key is not None and key==self.observed_source:return
  super().observe(raw);self.observed_source=key
  for a,m in self.motions.items():
   if (a,m['support']) not in self.control_sources:
    self.control_sources.add((a,m['support']));self.control_skill_bank.append(dict(action=a,model=copy.deepcopy(m)))
 def models_for(self,body):
  out={}
  for q in self.control_skill_bank:
   m=q['model'];b=m['after']
   if b['ink']==body['ink'] and b['box'][2:]==body['box'][2:]:out[q['action']]=copy.deepcopy(m)
  return out
 def respond(self,raw):
  if self.level==raw['levels_completed'] and raw['state']=='NOT_FINISHED' and self.previous and self.previous['action']!=0 and self.grid:self.observe(raw)
  else:self.size_plan=None
  self.ranged_excluded_inks={b['reference']['ink']for m in self.body_program_memory if m['effect']=='observed_body_relocation' for b in self.program_bindings if b['reference']['indices']==m['indices']}
  if self.moving and self.level==raw['levels_completed'] and raw['state']=='NOT_FINISHED':
   for a,m in self.models_for(self.moving).items():
    if a not in self.motions:self.motions[a]=m;self.retrieved_controls.append(dict(action=a,source=m['support'],at=self.t))
  if self.size_plan:
   p=self.size_plan
   if p['phase']=='approach':
    parents,_=reachable(self,raw);route=path(parents,tuple(p['pose'])) if tuple(p['pose']) in parents else None
    if route:return self.answer(raw,route[0],{},'size_prerequisite_approach',dict(size_precondition=copy.deepcopy(p),route=route))
    if route is None:self.size_plan=None
    else:
     p['phase']='edit';p['start']=self.t;p['editor']=ProgramEditLoop(p['binding']['points'],self.grid,self.t);self.program_editors.append(p['editor']);self.ranged=None;self.experiment=None;self.contact=None
   if self.size_plan and p['phase']=='edit':
    proposal=p['editor'].propose(raw)
    if proposal:return self.answer(raw,proposal['action'],proposal['data'],'size_prerequisite_edit',dict(edit=proposal['certificate'],edit_start=p['start'],size_precondition={k:copy.deepcopy(v) for k,v in p.items() if k!='editor'}))
    self.size_plan=None;self.ranged=None;self.experiment=None;self.heading_witness=None;self.orientations={};self.exploring=False;self.edit=None
  if self.moving and not self.edit and not self.ranged and self.level==raw['levels_completed'] and raw['state']=='NOT_FINISHED' and self.body_program_memory:
   parents,bg=reachable(self,raw);body=self.moving;h,w=body['box'][2:]
   refs={b['reference']['ink'] for b in self.program_bindings};excluded=[self.grid['box']]+[p['panel'] for p in programs(raw['frame'],self.grid)]
   targets=[o for o in objects(raw['frame'],excluded) if not o.get('parts') and o['ink'] in refs and min(o['box'][2:])>=2]
   def aligned(q,size,lm):
    y,x,hh,ww=lm['box'];dy=q[0]+(size-1)/2-y-(hh-1)/2;dx=q[1]+(size-1)/2-x-(ww-1)/2
    return (abs(dy)<1 and 2<=abs(dx)<=24) or (abs(dx)<1 and 2<=abs(dy)<=24)
   growth=[]
   for m in self.body_program_memory:
    if m['after']['box'][2:]!=body['box'][2:] or m['before']['box'][2]<=h:continue
    b=next((b for b in self.program_bindings if b['reference']['indices']==m['indices']),None)
    if b:growth.append((m,b))
   if growth and targets and not any(aligned(q,h,lm) for q in parents for lm in targets):
    m,b=growth[-1];size=m['before']['box'][2];models=self.models_for(m['before']);choices=[]
    for q in parents:
     key=(self.level,q,size)
     if key in self.size_plan_attempts or not(0<=q[0]<=64-size and 0<=q[1]<=64-size):continue
     if any(raw['frame'][y][x]==bg for y in range(q[0],q[0]+size) for x in range(q[1],q[1]+size)):continue
     test=SimpleNamespace(moving=dict(body,box=q+(size,size)),motions=models,blocked=set(),program_index=0,grid=self.grid)
     reach,_=reachable(test,raw)
     aims=[(len(path(reach,p)),p,lm) for p in reach for lm in targets if aligned(p,size,lm)]
     if aims:
      n,pose,lm=min(aims,key=lambda a:(a[0],a[1]));route=path(parents,q);choices.append((len(route)+n,q,route,lm))
    if choices:
     _,q,route,lm=min(choices,key=lambda a:(a[0],a[1]));self.size_plan_attempts.add((self.level,q,size));self.size_plan=dict(phase='approach',pose=q,size=size,binding=copy.deepcopy(b),effect_source=m['source'],landmark=copy.deepcopy(lm),hypothesis='test_size_change_to_enable_exact_alignment')
     if route:return self.answer(raw,route[0],{},'size_prerequisite_approach',dict(size_precondition=copy.deepcopy(self.size_plan),route=route))
  r=super().respond(raw)
  if r['done'] and raw['state']=='NOT_FINISHED' and self.desired_program is not None:
   binding=next((b for b in self.program_bindings if b['reference']['ink']==self.desired_program),None);key=(self.level,self.desired_program)
   if binding and key not in self.live_alternative_attempts:
    self.live_alternative_attempts.add(key);self.ranged=None;self.ranged_steps=0;self.exploring=False;self.experiment=None;self.contact=None;chosen=binding['points'];self.programs=[chosen]+[p for p in self.programs if p!=chosen];self.program_index=0;self.edit=ProgramEditLoop(chosen,self.grid,self.t);self.program_editors.append(self.edit);self.edit_started_at=self.t;proposal=self.edit.propose(raw)
    if proposal:return self.answer(raw,proposal['action'],proposal['data'],'verify_input_edit',dict(edit=proposal['certificate'],edit_start=self.t,alternative_without_reset=True))
  return r
 def answer(self,raw,*args,**kwargs):
  r=super().answer(raw,*args,**kwargs)
  if not r['done']:r['certificate']['retrieved_controls']=copy.deepcopy(self.retrieved_controls);self.previous['certificate']=copy.deepcopy(r['certificate'])
  return r
