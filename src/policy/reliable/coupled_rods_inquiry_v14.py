import copy
from multi_endpoint_inquiry_v5 import Agent as Prior
from coupled_rods_scene_v12 import scene,key,plan
from visual_transform_learner import digest
class Agent:
 def __init__(self):self.prior=Prior();self.active=False;self.level=None;self.previous=None;self.pending=None;self.models={};self.tried={};self.steps=0;self.failed=[];self.roles=None;self.knowledge=[]
 def respond(self,obs):
  if self.level!=obs['levels_completed']:
   if self.models:self.knowledge.append(dict(roles=copy.deepcopy(self.roles),models=copy.deepcopy(self.models)))
   if self.active:self.prior.pending=None
   self.level=obs['levels_completed'];self.active=False;self.pending=None;self.models={};self.tried={};self.steps=0;self.roles=None
  sc=scene(obs,self.roles)
  if sc and self.roles is None:
   self.roles=copy.deepcopy(sc['roles'])
   for lesson in reversed(self.knowledge):
    if digest(lesson['roles'])==digest(self.roles) and all(len(m['delta'])==len(sc['state']) for m in lesson['models'].values()):self.models=copy.deepcopy(lesson['models']);break
  if not self.active:
   if not sc or obs['state']!='NOT_FINISHED':return self.prior.respond(obs)
   self.active=True
  if not sc or obs['state']!='NOT_FINISHED':return dict(action=None,data={},done=True,certificate=None,advisor='coupled_rods',diagnostics=dict(reason='unresolved_joint_visibility'))
  if self.pending:
   old,p=self.pending;e=dict(before=self.previous,action=6,data=dict(y=p['y']+1,x=p['x']+1),after=copy.deepcopy(obs));source=digest(e);k=key(p);delta=[b-a for a,b in zip(old['state'],sc['state'])]
   if len(old['state'])!=len(sc['state']):return dict(action=None,data={},done=True,certificate=None,advisor='coupled_rods',diagnostics=dict(reason='ambiguous_identity_after_interaction'))
   if any(delta):
    prior=self.models.get(k)
    if not prior or prior['delta']!=delta:self.models[k]=dict(delta=delta,support=[])
    self.models[k]['support'].append(dict(source=source,before=old,after=sc,button=p))
   else:self.failed.append(dict(source=source,button=p,before_state=list(old['state']),scope=digest(self.roles)))
  self.pending=None;p=None;path=None;reason='unresolved_joint_motion'
  if self.steps<240:
   for q in sc['buttons']:
    k=key(q)
    if self.tried.get(k,0)<1 and len(self.models.get(k,{}).get('support',[]))<2:p=q;reason='test_joint_click_effect';break
   if p is None:
    path=plan(sc,self.models,{(tuple(q['before_state']),key(q['button'])) for q in self.failed if q['scope']==digest(self.roles)})
    if path:p=next(q for q in sc['buttons'] if key(q)==path[0]);reason='compose_observed_joint_motion_around_barriers'
    else:
     candidates=[q for q in sc['buttons'] if len(self.models.get(key(q),{}).get('support',[]))<2 and self.tried.get(key(q),0)<5]
     if candidates:p=min(candidates,key=lambda q:(self.tried.get(key(q),0),key(q)));reason='confirm_joint_motion_from_another_configuration'
  c=None;data={};action=None
  if p:
   action=6;data=dict(y=p['y']+1,x=p['x']+1);self.tried[key(p)]=self.tried.get(key(p),0)+1;self.steps+=1;c=dict(kind='coupled_rods_hypothesis',context=digest(obs),action=6,scene=sc,button=p,models=copy.deepcopy(self.models),path=path,failed=copy.deepcopy(self.failed),goal_is_hypothesis=True);self.pending=(copy.deepcopy(sc),copy.deepcopy(p));self.previous=copy.deepcopy(obs)
  return dict(action=action,data=data,done=p is None,certificate=c,advisor='coupled_rods',diagnostics=dict(reason=reason,steps=self.steps,models=len(self.models),retained_worlds=len(self.knowledge)))
