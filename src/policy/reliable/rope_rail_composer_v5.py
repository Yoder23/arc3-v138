"""Replan rail deposition from legal feedback; retain successful and refuted model predictions."""
import copy
from rope_sequence_inquiry_v5 import Agent as Prior
from rope_motion_hypotheses_v2 import scene,step,MODELS
from rope_rail_planning_v5 import goals,plan
from visual_transform_learner import digest
class Agent:
 def __init__(self):self.prior=Prior();self.level=None;self.context=None;self.goal=[];self.sequence=[];self.previous=None;self.last=None;self.history=[];self.steps=0;self.active=False;self.failures={};self.models={k:dict(matched=0,refuted=0,refutations=[]) for k in MODELS};self.model='source_all';self.previous_scene=None;self.previous_context=None
 def respond(self,o):
  c=scene(o)
  if self.previous is not None:
   e=dict(before=self.previous,action=self.last['action'],data=self.last['data'],after=copy.deepcopy(o));q=dict(source=digest(e),progress=o['levels_completed']>self.previous['levels_completed'] or o['state']=='WIN')
   if c and self.previous_scene and self.previous_context and not q['progress'] and o['state']=='NOT_FINISHED' and self.last['action'] in (1,2,3,4):
    q['model_matches']={}
    for name,fn in MODELS.items():
     matched=fn(self.previous_scene['state'],self.last['action'],self.previous_context)==c['state'];q['model_matches'][name]=matched;self.models[name]['matched' if matched else 'refuted']+=1
     if not matched:self.models[name]['refutations'].append(q['source'])
    best=min(self.models,key=lambda name:(self.models[name]['refuted'],-self.models[name]['matched']))
    if best!=self.model:self.model=best;self.sequence=[]
   if self.last.get('certificate',{}).get('kind')=='rope_rail_composition':
    q['prediction_matched']=bool(c and list(c['state'])==self.last['certificate']['prediction']);q['terminal']=q['progress']
    if not q['prediction_matched'] and not q['terminal']:
     self.sequence=[];self.failures.setdefault(digest(self.previous),[]).append(self.last['action'])
   self.history.append(q)
  if self.level!=o['levels_completed']:
   self.level=o['levels_completed'];self.context=copy.deepcopy(c);self.goal=goals(o,c) if c else [];self.sequence=[];self.steps=0;self.active=bool(self.goal)
   if self.active:self.prior.previous=None;self.prior.last=None
  if not self.active:r=self.prior.respond(o)
  else:
   a=None;info={}
   if c and o['state']=='NOT_FINISHED' and self.steps<180 and sum(map(len,self.failures.values()))<12:
    if not self.sequence:self.sequence,info=plan(c['state'],dict(self.context,model=self.model),self.goal)
    if self.sequence:a=self.sequence.pop(0)
   cert=None
   if a is not None:
    self.steps+=1;cert=dict(kind='rope_rail_composition',context=digest(o),action=a,scene=c,initial_scene=self.context,goals=self.goal,model=self.model,models=copy.deepcopy(self.models),remaining_plan=self.sequence[:],prediction=list(step(c['state'],a,dict(self.context,model=self.model))),history=copy.deepcopy(self.history),goal_is_hypothesis=True)
   r=dict(action=a,data={},done=a is None,certificate=cert,advisor='rope_rail_composer',diagnostics=dict(reason='compose_retained_motion_with_visible_rail_goals',steps=self.steps,search=info,refutations=sum(map(len,self.failures.values()))))
  self.previous=copy.deepcopy(o);self.previous_scene=copy.deepcopy(c);self.previous_context=copy.deepcopy(self.context);self.last=copy.deepcopy(r);return r
