"""Transfer tested control functions, run discriminating trials, and plan from visible goals."""
import copy
from articulated_rod_inquiry_v4 import Agent as Prior
from rod_forest_scene_v2 import scene,key
from rod_forest_model_v6 import topology,fit,predict,constraints
from rod_forest_inverse_goal_v2 import plan
from visual_transform_learner import digest
class Agent:
 def __init__(self):self.prior=Prior();self.level=None;self.active=False;self.closed=False;self.roles=None;self.models={};self.pending=None;self.history=[];self.failed=[];self.boundary={};self.rule=[];self.sequence=[];self.steps=0;self.phase='joint';self.trials=0;self.turns=0;self.knowledge=[]
 def ctx(self,sc):return dict(sc,allow_offscreen_top_colors=sorted(self.boundary))
 def response(self,reason):return dict(action=None,data={},done=True,certificate=None,advisor='rod_forest_transfer',diagnostics=dict(reason=reason,steps=self.steps,retained_worlds=len(self.knowledge)))
 def respond(self,o):
  if self.level!=o['levels_completed']:
   if self.active:self.knowledge.append(dict(roles=self.roles,models=copy.deepcopy(self.models),boundary=copy.deepcopy(self.boundary),rule=copy.deepcopy(self.rule)));self.closed=True
   self.level=o['levels_completed'];self.active=False;self.roles=None;self.pending=None
  if self.closed:return self.response('new_goal_structure_preserve_tested_knowledge')
  sc=scene(o,self.roles)
  if not self.active:
   if not sc:return self.prior.respond(o)
   self.active=True;self.roles=copy.deepcopy(sc['roles']);self.initial=copy.deepcopy(sc);self.initial_source=digest(o);self.tree=topology(sc)
   if not self.tree:return self.response('ambiguous_assembly_topology')
   buttons=sc['buttons']+sc['turns']
   for p in buttons:
    options=[m for k,m in self.prior.models.items() if k.split(':',1)[1]==key(p).split(':',1)[1] and len(m['support'])>=2]
    if options:
     m=max(options,key=lambda m:len(m['support']));q=copy.deepcopy(m);q['model']['index']=next(i for i,b in enumerate(sc['bodies']) if b['color']==p['color']);self.models[key(p)]=q
   parents={b:a for a,b in self.tree['edges']};nodes=[i for i,group in enumerate(self.tree['descendants']) if i in parents and len(group)>1 and any(p['color']==sc['bodies'][i]['color'] for p in sc['turns'])];filled=[e for e in sc['ends'] if e['point'] in sc['goals']];single=[p for p in sc['turns'] if not any(q['color']==p['color'] for q in sc['buttons'])]
   if not nodes or len(filled)!=1 or len(single)!=1:return self.response('unresolved_experiment_roles')
   i=min(nodes,key=lambda i:len(self.tree['descendants'][i]));self.joint_button=next(p for p in sc['turns'] if p['color']==sc['bodies'][i]['color']);self.obstacle=single[0];self.filled=copy.deepcopy(filled[0])
  if not sc or o['state']!='NOT_FINISHED':return self.response('unresolved_scene_after_interaction')
  if self.pending:
   before,old,p,expected=self.pending;source=digest(dict(before=before,action=6,data=dict(y=p['y']+1,x=p['x']+1),after=o));i=next(i for i,b in enumerate(sc['bodies']) if b['color']==p['color']);k=key(p)
   for b in sc['bodies']:
    if b['part']['y']<0 and str(b['color']) in self.roles['fixed_lengths'] and b['color']==p['color'] and p['area']==5:self.boundary.setdefault(b['color'],dict(source=source,color=b['color']))
   oldctx=self.ctx(old);limits=constraints(oldctx)
   if p['area']==5:
    single=predict(old['state'],i,'rotate',1,self.tree,limits);joint=predict(old['state'],i,'rotate_joint',1,self.tree,limits)
    if tuple(sc['state'])!=tuple(single or old['state']) and joint==tuple(sc['state']):
     self.rule.append(dict(source=source,button=p));
     for m in self.models.values():
      if m['model']['mode']=='rotate':m['model']['mode']='rotate_joint'
   m=fit(oldctx,sc,p,self.tree)
   if m:
    if m['mode']=='rotate_joint' and not self.rule:m['mode']='rotate'
    if k not in self.models or self.models[k]['model']!=m:self.models[k]=dict(model=m,support=[])
    self.models[k]['support'].append(dict(source=source,button=p))
   same=old['state']==sc['state'];self.history.append(dict(source=source,observed_noop=same,prediction_matched=expected is not None and tuple(expected)==tuple(sc['state'])))
   if same:self.failed.append(dict(source=source,button=p,state=list(old['state'])))
   if expected is not None and tuple(expected)!=tuple(sc['state']):self.sequence=[]
  self.pending=None;p=None;path=None;reason=self.phase;ctx=self.ctx(sc);limits=constraints(ctx)
  if self.steps>=180:return self.response('bounded_joint_inquiry')
  if self.phase=='joint':
   if self.trials<3:p=self.joint_button;self.trials+=1
   else:self.phase='clearance'
  if p is None and self.phase=='clearance':
   m=self.models[key(self.obstacle)]['model'];candidate=predict(sc['state'],m['index'],m['mode'],m['amount'],self.tree,limits)
   if candidate is not None:p=self.obstacle;self.turns=1;self.phase='turn_obstacle'
   else:
    choices=[q for q in sc['buttons'] if q['color']==self.filled['color'] and key(q) in self.models and self.models[key(q)]['model']['amount']<0]
    if choices:p=choices[0]
  if p is None and self.phase=='turn_obstacle':
   if self.turns<3:p=self.obstacle;self.turns+=1
   else:self.phase='restore_goal'
  if p is None and self.phase=='restore_goal':
   e=next(e for e in sc['ends'] if e['color']==self.filled['color']);goal=self.filled['point'];j=sc['ends'].index(e);offset=6*len(sc['bodies'])+2*j;distance=sum(abs(a-b) for a,b in zip(e['point'],goal))
   if distance==0:self.phase='compose'
   else:
    for q in sc['buttons']:
     if q['color']!=e['color'] or key(q) not in self.models:continue
     m=self.models[key(q)]['model'];nxt=predict(sc['state'],m['index'],m['mode'],m['amount'],self.tree,limits)
     if nxt is not None and sum(abs(a-b) for a,b in zip(nxt[offset:offset+2],goal))<distance:p=q;break
  search={}
  if p is None and self.phase=='compose':
   if not self.sequence:self.sequence,search=plan(ctx,self.tree,self.models,{(tuple(q['state']),key(q['button'])) for q in self.failed})
   if self.sequence:path=self.sequence[:];p=next(q for q in sc['buttons']+sc['turns'] if key(q)==path[0]);self.sequence.pop(0)
  if p is None:return self.response('no_supported_goal_plan')
  m=self.models.get(key(p));prediction=None
  if m:
   q=m['model'];prediction=predict(sc['state'],q['index'],q['mode'],q['amount'],self.tree,limits)
  c=dict(kind='rod_forest_transferred_composition',context=digest(o),initial_source=self.initial_source,initial=self.initial,scene=sc,tree=self.tree,button=p,models=copy.deepcopy(self.models),boundary=list(copy.deepcopy(self.boundary).values()),rule_refutations=copy.deepcopy(self.rule),failed=copy.deepcopy(self.failed),path=path,goal_is_hypothesis=True,hidden_extent_is_hypothesis=True,transfer_is_hypothesis=True);self.pending=(copy.deepcopy(o),copy.deepcopy(sc),copy.deepcopy(p),prediction);self.steps+=1
  return dict(action=6,data=dict(y=p['y']+1,x=p['x']+1),done=False,certificate=c,advisor='rod_forest_transfer',diagnostics=dict(reason=self.phase,steps=self.steps,models=len(self.models),joint_rule_refutations=len(self.rule),learned_top_exceptions=len(self.boundary),search=search))
