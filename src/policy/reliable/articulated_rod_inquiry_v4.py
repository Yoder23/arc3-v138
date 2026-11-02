import copy
from coupled_panel_inquiry_v2 import Agent as Prior
from orientable_endpoint_scene_v4 import scene,key
from articulated_rod_model_v4 import topology,fit,plan,predict,constraints
from visual_transform_learner import digest
class Agent:
 def __init__(self):self.prior=Prior();self.level=None;self.active=False;self.pending=None;self.models={};self.tried={};self.steps=0;self.failed=[];self.knowledge=[];self.scope=None;self.tree=None;self.roles=None
 def respond(self,o):
  if self.level!=o['levels_completed']:
   if self.models:self.knowledge.append(dict(scope=self.scope,models=copy.deepcopy(self.models)))
   self.level=o['levels_completed'];self.active=False;self.pending=None;self.models={};self.tried={};self.steps=0;self.scope=None;self.tree=None;self.roles=None
  sc=scene(o,self.roles)
  if not self.active:
   if not sc or not topology(sc):
    if self.knowledge:return dict(action=None,data={},done=True,certificate=None,advisor='articulated_rods',diagnostics=dict(reason='new_goal_structure_requires_new_hypothesis',retained_worlds=len(self.knowledge)))
    return self.prior.respond(o)
   self.active=True;self.roles=copy.deepcopy(sc['roles']);self.tree=topology(sc);self.scope=digest(dict(tree=self.tree,colors=[b['color'] for b in sc['bodies']]))
   for q in reversed(self.knowledge):
    if q['scope']==self.scope:self.models=copy.deepcopy(q['models']);break
  if not sc or o['state']!='NOT_FINISHED':return dict(action=None,data={},done=True,certificate=None,advisor='articulated_rods',diagnostics=dict(reason='unresolved_rotated_geometry'))
  if self.pending:
   before,old,p=self.pending;source=digest(dict(before=before,action=6,data=dict(y=p['y']+1,x=p['x']+1),after=o));m=fit(old,sc,p,self.tree);k=key(p)
   if m:
    if k not in self.models or self.models[k]['model']!=m:self.models[k]=dict(model=m,support=[])
    self.models[k]['support'].append(dict(source=source,button=p))
   else:self.failed.append(dict(source=source,state=list(old['state']),button=p,scope=self.scope))
  self.pending=None;buttons=sc['turns']+sc['buttons'];p=None;path=None;reason='no_supported_plan';blocked={(tuple(q['state']),key(q['button'])) for q in self.failed if q['scope']==self.scope}
  if self.steps<180:
   ps=[q for q in buttons if self.tried.get(key(q),0)<2 and len(self.models.get(key(q),{}).get('support',[]))<2 and (tuple(sc['state']),key(q)) not in blocked]
   if ps:p=ps[0];reason='test_subtree_orientation_and_extension'
   else:
    path=plan(sc,self.tree,self.models,blocked)
    if path:p=next(q for q in buttons if key(q)==path[0]);reason='compose_tested_rotations_and_extensions'
    else:
     ps=[q for q in buttons if len(self.models.get(key(q),{}).get('support',[]))<2 and self.tried.get(key(q),0)<5 and (tuple(sc['state']),key(q)) not in blocked]
     if ps:p=min(ps,key=lambda q:(self.tried.get(key(q),0),key(q)));reason='test_alternative_after_failed_action'
  c=None;data={}
  if p:
   data=dict(y=p['y']+1,x=p['x']+1);self.tried[key(p)]=self.tried.get(key(p),0)+1;self.steps+=1;c=dict(kind='articulated_rod_composition',context=digest(o),scene=sc,tree=self.tree,scope=self.scope,button=p,models=copy.deepcopy(self.models),failed=copy.deepcopy(self.failed),path=path,goal_is_hypothesis=True);self.pending=(copy.deepcopy(o),copy.deepcopy(sc),copy.deepcopy(p))
  return dict(action=6 if p else None,data=data,done=p is None,certificate=c,advisor='articulated_rods',diagnostics=dict(reason=reason,steps=self.steps,models=len(self.models),retained_worlds=len(self.knowledge)))
