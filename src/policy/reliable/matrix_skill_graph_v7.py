"""Compose observed movement, size, remote-interaction and relocation skills.
Every macro is a hypothesis; a fresh observation replans after each actual action.
"""
import copy
from collections import Counter
from types import SimpleNamespace
from matrix_relocation_goal_v2 import Agent as Base
from matrix_motion_learner_v6 import objects,grids
from matrix_reference_programs_v1 import programs
from matrix_intermediate_learner_v3 import reachable as raw_reachable,path,inside,gap
from observed_program_completion_v1 import ProgramEditLoop

def pads(raw,ink,bg):
 f=raw['frame'];dots={(o['box'][0],o['box'][1])for o in objects(f)if o['ink']==ink and o['box'][2:]==(1,1)};out=[]
 for y,x in sorted(dots):
  for size in range(2,7):
   edge=size+1
   if all(p in dots for p in ((y,x+edge),(y+edge,x),(y+edge,x+edge))) and all(f[v][u]!=bg for v in range(y+1,y+1+size)for u in range(x+1,x+1+size)):
    out.append(dict(box=(y,x,size+2,size+2),pose=(y+1,x+1),size=size,ink=ink,corners=[(y,x),(y,x+edge),(y+edge,x),(y+edge,x+edge)]))
 return out

def aims(body,parents,targets):
 h,w=body['box'][2:];out=[]
 for lm in targets:
  y,x,hh,ww=lm['box'];cy=y+(hh-1)/2;cx=x+(ww-1)/2
  for q in parents:
   by=q[0]+(h-1)/2;bx=q[1]+(w-1)/2
   if abs(by-cy)<=1:direction=(0,1 if cx>bx else -1);distance=abs(cx-bx)
   elif abs(bx-cx)<=1:direction=(1 if cy>by else -1,0);distance=abs(cy-by)
   else:continue
   if 2<=distance<=24:out.append((len(path(parents,q)),q,lm,direction))
 return out

class Agent(Base):
 def __init__(self,*args,**kwargs):
  super().__init__(*args,**kwargs);self.smart_active=False;self.skill_editor=None;self.skill_task=None;self.shot_attempts=set();self.transfer_attempts=set();self.skill_outcomes=[];self.skill_resets=Counter();self.skill_pending=None;self.geometry_alternatives=set();self.barrier_evidence=[]
 def reachable(self,agent,raw):
  if not self.barrier_evidence:return raw_reachable(agent,raw)
  blocked={q['ink']for q in self.barrier_evidence};bg=Counter(v for row in raw['frame']for v in row).most_common(1)[0][0];masked=dict(raw,frame=[[bg if v in blocked else v for v in row]for row in raw['frame']]);return raw_reachable(agent,masked)
 def clear_aims(self,raw,body,parents,targets):
  bg=Counter(v for row in raw['frame']for v in row).most_common(1)[0][0];blocked={bg}|{q['ink']for q in self.barrier_evidence};out=[]
  for n,q,lm,d in aims(body,parents,targets):
   y=q[0]+(body['box'][2]-1)//2;x=q[1]+(body['box'][3]-1)//2;seen=[]
   for k in range(1,30):
    yy=y+k*d[0];xx=x+k*d[1]
    if not(0<=yy<64 and 0<=xx<64):break
    if inside(yy,xx,lm['box']):out.append((n,q,lm,d));break
    if inside(yy,xx,q+tuple(body['box'][2:])):continue
    if raw['frame'][yy][xx]in blocked:break
  return out
 def capture_barrier(self,raw):
  old=self.previous;task=self.skill_task
  if not old or old['action']!=6 or not task or task.get('kind')!='test_remote_interaction'or old['raw']['levels_completed']!=raw['levels_completed']:return
  lm=task['landmark'];y,x,h,w=lm['box'];before=old['raw']['frame'];after=raw['frame'];ink=before[y+(h-1)//2][x+(w-1)//2]
  if ink==lm['ink']or not all(after[y+dy][x+dx]!=lm['ink']for dy,dx in lm['shape']):return
  changes=[(v,u,ink,after[v][u])for v in range(64)for u in range(64)if before[v][u]==ink and after[v][u]!=ink and not inside(v,u,lm['box'])and not inside(v,u,self.grid['box'])]
  if changes and not any(q['source']==old['source']for q in self.barrier_evidence):self.barrier_evidence.append(dict(source=old['source'],ink=ink,landmark=copy.deepcopy(lm),changes=changes,hypothesis='remote_region_with_switch_center_ink_blocks_ordinary_routes'))
 def skill_models(self,body):
  out={}
  for a in (1,2,3,4):
   options=[q['model']for q in self.control_skill_bank if q['action']==a and q['model']['before']['box'][2:]==body['box'][2:] and q['model']['after']['box'][2:]==body['box'][2:] and q['model']['after']['ink']==body['ink']]
   if options:
    counts=Counter(tuple(m['delta'])for m in options);best=max(counts,key=lambda d:(counts[d],sum(map(abs,d))));out[a]=copy.deepcopy(next(m for m in reversed(options)if tuple(m['delta'])==best))
  return out
 def capture_effect(self,raw):
  old=self.previous
  if not old or old['action']!=6 or old['source']in self.effect_sources or old['raw']['levels_completed']!=raw['levels_completed']:return
  c=old['certificate'];edit=c.get('edit');grid=c.get('grid')
  if not edit or not grid:return
  selected=[q['point']for q in edit.get('previous_evidence',[])if q.get('changed')]+[edit['point']]
  b=next((b for b in c.get('program_bindings',[])if set(map(tuple,b['points']))==set(map(tuple,selected))),None)
  if not b:return
  before=[o for o in objects(old['raw']['frame'],[grid['box']])if o.get('parts')];after=[o for o in objects(raw['frame'],[grid['box']])if o.get('parts')];pairs=[(a,z)for a in before for z in after if a['ink']==z['ink']and a['box']!=z['box']]
  if len(pairs)==1:
   a,z=pairs[0];self.effect_sources.add(old['source']);self.body_program_memory.append(dict(level=raw['levels_completed'],source=old['source'],binding=copy.deepcopy(b),before=a,after=z,indices=b['reference']['indices'],effect='observed_body_size_change'if a['box'][2:]!=z['box'][2:]else'observed_body_relocation',causality='single_program_intervention_hypothesis'))
 def start_skill(self,raw,binding,task):
  self.skill_editor=ProgramEditLoop(binding['points'],self.grid,self.t);self.program_editors.append(self.skill_editor);self.skill_task=dict(task,binding=copy.deepcopy(binding),start=self.t);return self.edit_skill(raw)
 def edit_skill(self,raw):
  p=self.skill_editor.propose(raw)
  if p:return self.answer(raw,p['action'],p['data'],'composed_input_edit',dict(edit=p['certificate'],edit_start=self.skill_task['start'],skill_task=copy.deepcopy(self.skill_task)))
  self.skill_outcomes.append(dict(task=self.skill_task,completed=self.skill_editor.completed(raw),observed_at=self.t));self.skill_editor=None;self.skill_task=None;return None
 def respond(self,raw):
  if not self.smart_active:
   r=super().respond(raw)
   if any(m['effect']=='observed_body_relocation'for m in self.body_program_memory)and r.get('certificate',{}).get('tag')=='motion_inquiry':self.smart_active=True;self.edit=None;self.ranged=None;self.experiment=None;self.contact=None
   return r
  if raw['state']=='WIN':return dict(done=True,action=None,data={})
  if raw['state']=='GAME_OVER':
   self.skill_editor=None;self.skill_pending=None;self.moving=None;self.skill_resets[self.level]+=1
   if self.skill_resets[self.level]>3:return dict(done=True,action=None,data={})
   return self.answer(raw,0,{},'reset_after_failure')
  fresh=self.level!=raw['levels_completed']or self.previous and self.previous['action']==0
  if fresh:
   self.level=raw['levels_completed'];self.skill_editor=None;self.skill_pending=None;self.ranged=None;self.contact=None;self.experiment=None;self.edit=None;self.heading_witness=None;self.orientations={};self.blocked=set();self.moving=None;self.motions={}
   found=grids(raw['frame'])
   if not found:return dict(done=True,action=None,data={})
   self.grid=dict(found[0],observed_at=self.t);self.program_bank_bound_at=self.t;self.program_bindings=[]
   for p in programs(raw['frame'],self.grid):
    points=[(self.grid['cells'][i][1]+(self.grid['cells'][i][3]-1)//2,self.grid['cells'][i][0]+(self.grid['cells'][i][2]-1)//2)for i in p['indices']]
    self.program_bindings.append(dict(source=self.t,reference=p,grid=copy.deepcopy(self.grid),points=points,hypothesis='copy_visible_reference_mask_to_input_cells'))
   self.programs=[b['points']for b in self.program_bindings];self.program_index=0
  else:self.observe(raw);self.capture_barrier(raw);self.capture_effect(raw)
  palettes={tuple(m['before']['ink'])for m in self.body_program_memory};obs=objects(raw['frame'],[self.grid['box']]);bodies=[o for o in obs if o.get('parts')and tuple(o['ink'])in palettes]
  if len(bodies)!=1:return dict(done=True,action=None,data={})
  self.moving=bodies[0];body=self.moving;self.motions=self.skill_models(body)
  self.goals=[dict(o,observed_at=self.t)for o in obs if not o.get('parts')and o['ink']in body['ink']and len(o['shape'])==o['box'][2]*o['box'][3]and o['box'][2]==o['box'][3]and min(o['box'][2:])>=2]
  if self.skill_editor:
   r=self.edit_skill(raw)
   if r:return r
  parents,bg=self.reachable(self,raw);excluded=[self.grid['box']]+[b['reference']['panel']for b in self.program_bindings]
  relocation=[(m,b)for m in self.body_program_memory for b in self.program_bindings if m['effect']=='observed_body_relocation'and m['indices']==b['reference']['indices']]
  transforms=[(m,b)for m in self.body_program_memory for b in self.program_bindings if m['effect']=='observed_body_size_change'and m['indices']==b['reference']['indices']]
  other={b['reference']['ink']for m,b in relocation+transforms};target_inks={b['reference']['ink']for b in self.program_bindings}-other
  targets=[o for o in objects(raw['frame'],excluded)if not o.get('parts')and o['ink']in target_inks and min(o['box'][2:])>=2]
  goals=[(len(path(parents,q)),q,g)for g in self.goals if g['box'][2:]==body['box'][2:]for q in parents if inside(q[0],q[1],g['box'])]
  if goals:
   _,q,g=min(goals,key=lambda q:(q[0],q[1]));route=path(parents,q)
   if route:return self.answer(raw,route[0],{},'composed_goal_route',dict(skill_route=route,skill_goal=g))
  if self.skill_pending:
   lm=self.skill_pending;self.skill_pending=None
   if any(o['box']==lm['box']and o['ink']==lm['ink']for o in targets):
    b=next(b for b in self.program_bindings if b['reference']['ink']==lm['ink']);self.shot_attempts.add((self.level,tuple(body['box']),tuple(lm['box']),lm['ink']))
    return self.start_skill(raw,b,dict(kind='test_remote_interaction',landmark=dict(lm,observed_at=self.t)))
  choices=[v for v in self.clear_aims(raw,body,parents,targets)if (self.level,tuple(v[1])+tuple(body['box'][2:]),tuple(v[2]['box']),v[2]['ink'])not in self.shot_attempts]
  if choices:
   n,q,lm,direction=min(choices,key=lambda v:(v[0],v[1],v[2]['box']));route=path(parents,q)
   if route:return self.answer(raw,route[0],{},'composed_interaction_approach',dict(skill_route=route,skill_landmark=dict(lm,observed_at=self.t)))
   controls=[a for a,m in self.motions.items()if tuple((v>0)-(v<0)for v in m['delta'])==direction]
   if controls:self.shot_attempts.add((self.level,tuple(body['box']),tuple(lm['box']),lm['ink']));self.skill_pending=copy.deepcopy(lm);return self.answer(raw,controls[0],{},'composed_interaction_orient',dict(skill_landmark=dict(lm,observed_at=self.t),skill_direction=direction))
  # A small transported body may need to regain the goal's geometry locally.
  if not targets and self.goals:
   resize_options=[]
   for mm,bb in transforms:
    sizes={mm['before']['box'][2],mm['after']['box'][2]}
    if body['box'][2]not in sizes:continue
    size=next((z for z in sizes if z!=body['box'][2]),None)
    if size is None or not any(g['box'][2:]==(size,size)for g in self.goals):continue
    models=self.skill_models(dict(body,box=(0,0,size,size)))
    for q in parents:
     for yy in range(q[0]-max(0,size-body['box'][2]),q[0]+1):
      for xx in range(q[1]-max(0,size-body['box'][3]),q[1]+1):
       if not(0<=yy<=64-size and 0<=xx<=64-size)or any(raw['frame'][v][u]==bg for v in range(yy,yy+size)for u in range(xx,xx+size)):continue
       virtual=SimpleNamespace(moving=dict(body,box=(yy,xx,size,size)),motions=models,blocked=set(),program_index=0,grid=self.grid);reach,_=self.reachable(virtual,raw)
       routes=[path(reach,p)for p in reach for g in self.goals if g['box'][2:]==(size,size)and inside(p[0],p[1],g['box'])]
       if routes:resize_options.append((len(path(parents,q))+min(map(len,routes)),q,mm,bb,size,(yy,xx)))
   if resize_options:
    _,q,mm,bb,size,anchor=min(resize_options,key=lambda v:(v[0],v[1]));route=path(parents,q)
    if route:return self.answer(raw,route[0],{},'composed_size_approach',dict(skill_route=route,skill_size=size,skill_growth_anchor=anchor))
    return self.start_skill(raw,bb,dict(kind='test_size_for_goal',effect_source=mm['source'],size=size,growth_anchor=anchor))
  transfers=[]
  for m,b in relocation:
   for pad in pads(raw,b['reference']['ink'],bg):
    size=pad['size'];testbody=dict(body,box=pad['pose']+(size,size));models=self.skill_models(testbody)
    if len(models)<2:continue
    virtual=SimpleNamespace(moving=testbody,motions=models,blocked=set(),program_index=0,grid=self.grid);reach,_=self.reachable(virtual,raw)
    goal_routes=[path(reach,q)for g in self.goals if min(g['box'][2:])>=size for q in reach if inside(q[0],q[1],g['box'])]
    target_routes=self.clear_aims(raw,testbody,reach,targets)
    if not goal_routes and not target_routes:continue
    if tuple(body['box'][:2])==pad['pose']and body['box'][2]==size:continue
    cost=min([len(r)for r in goal_routes]or[v[0]for v in target_routes]);key=(self.level,body['box'][2],any(tuple(body['box'][:2])==pp['pose']for pp in pads(raw,b['reference']['ink'],bg)),tuple(pad['pose']),size,tuple(tuple(o['box'])for o in targets))
    if key in self.transfer_attempts:continue
    transfers.append((not bool(goal_routes),size!=body['box'][2],cost,pad,m,b,key))
  if transfers:
   _,_,cost,pad,m,b,key=min(transfers,key=lambda v:(v[0],v[1],v[2],v[3]['pose']));size=pad['size']
   if size!=body['box'][2]:
    resize=[(mm,bb)for mm,bb in transforms if {mm['before']['box'][2],mm['after']['box'][2]}=={size,body['box'][2]}]
    poses=[q for q in parents if 0<=q[0]<=64-size and 0<=q[1]<=64-size and all(raw['frame'][y][x]!=bg for y in range(q[0],q[0]+size)for x in range(q[1],q[1]+size))]
    if resize and poses:
     q=min(poses,key=lambda q:(len(path(parents,q)),q));route=path(parents,q)
     if route:return self.answer(raw,route[0],{},'composed_size_approach',dict(skill_route=route,skill_pad=pad,skill_size=size))
     mm,bb=resize[-1];return self.start_skill(raw,bb,dict(kind='test_size_for_relocation',pad=pad,effect_source=mm['source'],size=size))
   else:
    self.transfer_attempts.add(key);return self.start_skill(raw,b,dict(kind='test_relocation_for_route',pad=pad,effect_source=m['source']))
  # A visible pad is only a destination hypothesis. Repeated observed relocation
  # to the wrong region warrants testing the other learned body geometry.
  alternatives=[]
  for mm,bb in transforms:
   sizes={mm['before']['box'][2],mm['after']['box'][2]}
   if body['box'][2]not in sizes:continue
   size=next((z for z in sizes if z!=body['box'][2]),None);key=(self.level,size,tuple(tuple(o['box'])for o in targets))
   if size is None or key in self.geometry_alternatives:continue
   for q in parents:
    for yy in range(q[0]-max(0,size-body['box'][2]),q[0]+1):
     for xx in range(q[1]-max(0,size-body['box'][3]),q[1]+1):
      if 0<=yy<=64-size and 0<=xx<=64-size and all(raw['frame'][v][u]!=bg for v in range(yy,yy+size)for u in range(xx,xx+size)):
       alternatives.append((len(path(parents,q)),q,mm,bb,size,key,(yy,xx)))
  if alternatives:
   _,q,mm,bb,size,key,anchor=min(alternatives,key=lambda v:(v[0],v[1]));route=path(parents,q)
   if route:return self.answer(raw,route[0],{},'composed_size_approach',dict(skill_route=route,skill_size=size,skill_growth_anchor=anchor))
   self.geometry_alternatives.add(key);return self.start_skill(raw,bb,dict(kind='test_alternative_geometry_after_relocation_miss',effect_source=mm['source'],size=size,growth_anchor=anchor))
  return dict(done=True,action=None,data={})

 def answer(self,raw,*args,**kwargs):
  r=super().answer(raw,*args,**kwargs)
  if not r['done']:
   r['certificate']['composition_memory']=dict(barriers=copy.deepcopy(self.barrier_evidence),outcomes=copy.deepcopy(self.skill_outcomes),relocation_attempts=copy.deepcopy(sorted(self.transfer_attempts)),shot_attempts=copy.deepcopy(sorted(self.shot_attempts)))
   self.previous['certificate']=copy.deepcopy(r['certificate'])
  return r
