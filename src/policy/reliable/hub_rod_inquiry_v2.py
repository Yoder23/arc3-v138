import copy
from rod_forest_transfer_v1 import Agent as Prior
from hub_rod_scene_v2 import scene,key
from hub_rod_model_v2 import topology,limits,predict,plan,matches
from visual_transform_learner import digest
class Agent:
 def __init__(self):self.prior=Prior();self.active=False;self.level=None;self.initial=None;self.initial_source=None;self.state=None;self.models={};self.pending=None;self.history=[];self.failed=[];self.sequence=[];self.steps=0;self.refutations=[];self.knowledge=[];self.tried={}
 def stop(self,reason):return dict(action=None,data={},done=True,certificate=None,advisor='hub_rod_inquiry',diagnostics=dict(reason=reason,steps=self.steps,models=len(self.models)))
 def respond(self,o):
  if self.level!=o['levels_completed']:
   if self.active:self.knowledge.append(dict(initial=self.initial,models=self.models,history=self.history,failed=self.failed));self.active=False
   self.level=o['levels_completed'];self.initial=None;self.pending=None;self.sequence=[];self.steps=0;self.models={};self.history=[];self.failed=[];self.refutations=[];self.tried={}
  if not self.active:
   sc=scene(o)
   if not sc:return self.prior.respond(o)
   self.active=True;self.initial=copy.deepcopy(sc);self.initial_frame=copy.deepcopy(o['frame']);self.initial_source=digest(o);self.state=tuple(sc['state']);self.tree=topology(sc)
   for p in sc['buttons']+sc['turns']:
    pool=self.prior.prior.models if p['area']==5 else (self.prior.models or self.prior.prior.models)
    options=[m for k,m in pool.items() if k.split(':',1)[1]==key(p).split(':',1)[1] and len(m['support'])>=2]
    lessons=[m for lesson in self.knowledge for k,m in lesson['models'].items() if k.split(':',1)[1]==key(p).split(':',1)[1] and m['support']]
    if lessons:
     m=max(lessons,key=lambda m:len(m['support']));self.models[key(p)]=dict(color=p['color'],mode=m['mode'],amount=m['amount'],support=copy.deepcopy(m['support']))
    elif options:
     m=max(options,key=lambda m:len(m['support']));self.models[key(p)]=dict(color=p['color'],mode='rotate' if p['area']==5 else 'extend',amount=m['model']['amount'],support=copy.deepcopy(m['support']))
  sc=self.initial
  if self.pending:
   before,p,expected=self.pending;source=digest(dict(before=before,action=6,data=dict(y=p['y']+1,x=p['x']+1),after=o));m=self.models.get(key(p));mode='rotate' if p['area']==5 else 'extend'
   if matches(sc,self.state,self.initial_frame,o['frame']):
    self.failed.append(dict(source=source,button=p,state=list(self.state)));self.sequence=[];self.history.append(dict(source=source,button=p,state=list(self.state),outcome='observed_noop'))
   else:
    hits=[]
    for amount in (-1,1) if mode=='rotate' else (-3,3):
     nxt=predict(self.state,sc,self.tree,p['color'],mode,amount,limits(sc,True),check=False)
     if nxt and matches(sc,nxt,self.initial_frame,o['frame']):hits.append((amount,nxt))
    if len(hits)!=1:return self.stop('refuted_motion_requires_new_hypothesis')
    amount,nxt=hits[0];outcome='predicted_transition'
    if m is not None and m['amount']!=amount:self.refutations.append(dict(source=source,old=copy.deepcopy(m),new_amount=amount));self.sequence=[];outcome='alternative_transition'
    if m is None or m['amount']!=amount:self.models[key(p)]=m=dict(color=p['color'],mode=mode,amount=amount,support=[])
    m['support'].append(dict(source=source,button=p,origin='hub'));self.state=tuple(nxt);self.history.append(dict(source=source,button=p,state=list(self.state),outcome=outcome))
   self.pending=None
  if o['state']!='NOT_FINISHED':return self.stop('terminal_observation')
  if self.steps>=180:return self.stop('bounded_hub_inquiry')
  stats={};p=None;path=None;known=len(self.models)==len(sc['buttons']+sc['turns'])
  if not known:
   candidates=[p for p in sc['turns']+sc['buttons'] if key(p) not in self.models and self.tried.get(key(p),0)==0]
   if candidates:p=candidates[0]
  if p is None:
   if not self.sequence:self.sequence,stats=plan(dict(sc,state=self.state),self.models,True,{(tuple(q['state']),key(q['button'])) for q in self.failed})
   if self.sequence:path=self.sequence[:];p=next(p for p in sc['buttons']+sc['turns'] if key(p)==path[0]);self.sequence.pop(0)
   else:
    failed={(tuple(q['state']),key(q['button'])) for q in self.failed};candidates=[p for p in sc['turns']+sc['buttons'] if key(p) not in self.models and self.tried.get(key(p),0)<6 and (self.state,key(p)) not in failed]
    if candidates:p=min(candidates,key=lambda p:(self.tried.get(key(p),0),key(p)))
  if p is None:return self.stop('no_remaining_supported_goal_plan')
  self.tried[key(p)]=self.tried.get(key(p),0)+1;m=self.models.get(key(p));expected=predict(self.state,sc,self.tree,m['color'],m['mode'],m['amount'],limits(sc,True)) if m else None
  c=dict(kind='hub_rod_composition',context=digest(o),initial_source=self.initial_source,initial=sc,state=list(self.state),tree=self.tree,button=p,models=copy.deepcopy(self.models),history=copy.deepcopy(self.history),failed=copy.deepcopy(self.failed),refutations=copy.deepcopy(self.refutations),path=path,goal_is_hypothesis=True,hidden_extent_is_hypothesis=True,transfer_is_hypothesis=True);self.pending=(copy.deepcopy(o),copy.deepcopy(p),expected);self.steps+=1
  return dict(action=6,data=dict(y=p['y']+1,x=p['x']+1),done=False,certificate=c,advisor='hub_rod_inquiry',diagnostics=dict(reason='test_transferred_composition_and_replan_on_failure',steps=self.steps,refutations=len(self.refutations),failed_edges=len(self.failed),search=stats))
